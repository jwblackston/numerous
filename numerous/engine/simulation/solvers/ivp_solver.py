

from scipy.integrate import solve_ivp
from tqdm import tqdm
import numpy as np

from numerous.engine.simulation.solvers.base_solver import BaseSolver


"""
Wraper for scipy ivp solver.
"""
class IVP_solver(BaseSolver):

    def __init__(self, time, delta_t, numba_model, num_inner, max_event_steps, **kwargs):
        super().__init__()
        self.time = time
        self.num_inner = num_inner
        self.delta_t = delta_t
        self.numba_model = numba_model
        self.diff_function = numba_model.func
        self.max_event_steps = max_event_steps
        self.options = kwargs

    def solve(self):
        """
        solve the model.

        Returns
        -------
        Solution : 'OdeSoulution'
                returns the most recent OdeSolution from scipy

        """

        result_status = "Success"
        stop_condition = False
        sol = None
        event_steps = 0
        try:
            for t in tqdm(self.time[0:-1]):
                    step_not_finished = True
                    current_timestamp = t
                    while step_not_finished:
                        t_eval = np.linspace(current_timestamp, t + self.delta_t, self.num_inner + 1)

                        sol = solve_ivp(self.diff_function, (current_timestamp, t + self.delta_t), y0=self.y0, t_eval=t_eval,
                                        events=self.events, dense_output=True,
                                        **self.options)
                        step_not_finished = False
                        event_step = sol.status == 1

                        if sol.status == 0:
                            current_timestamp = t + self.delta_t
                        if event_step:
                            event_id = np.nonzero([x.size > 0 for x in sol.t_events])[0][0]
                            # solution stuck
                            stop_condition = False
                            if (abs(sol.t_events[event_id][0] - current_timestamp) < 1e-6):
                                event_steps += 1
                            else:
                                event_steps = 0

                            if event_steps > self.max_event_steps:
                                stop_condition = True
                            current_timestamp = sol.t_events[event_id][0]

                            step_not_finished = True

                            self.__end_step(self, sol.sol(current_timestamp), current_timestamp, event_id=event_id)
                        else:
                            if sol.success:
                                self.__end_step(self, sol.y[:, -1], current_timestamp)
                            else:
                                result_status = sol.message
                        if stop_condition:
                            break
                    if stop_condition:
                        result_status = "Stopping condition reached"
                        break
        except Exception as e:
            print(e)
            raise e
        finally:
            return sol, result_status


    def set_state_vector(self, states_as_vector):
        self.y0 = states_as_vector

    def register_endstep(self, __end_step):
        self.__end_step =__end_step

