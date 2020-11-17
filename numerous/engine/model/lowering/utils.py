from enum import IntEnum, unique
from model.lowering.source_gen import SourceGeneratorNumerous

import ast, astor

dot_dict, wrap_function


@unique
class VarTypes(IntEnum):
    CONSTANT=0
    PARAMETER=1
    DERIV=2
    STATE=3
    LOCAL=4
    TMP=5


def wrap_module(body):
    mod = ast.Module()
    mod.body = body
    return mod


def generate_code_file(mod_body, file,preamble="from numba import njit, carray, float64, float32\nimport numpy as np\n"):
    mod = wrap_module(mod_body)
    print('Generating Source')

    source = preamble + astor.to_source(mod, indent_with=' ' * 4, add_line_information=False, source_generator_class=SourceGeneratorNumerous)

    with open(file, 'w') as f:
        f.write(source)

    return source


############### Check variables and make sets for codegen

# Define helper functions to check the variables and sub lists
def non_unique_check(listname_, list_):
    if len(list_) > len(set(list_)):
        import collections
        raise ValueError(
            f'Non unique {listname_}: {[item for item, count in collections.Counter(list_).items() if count > 1]}')


def contains_dot(str_list):
    for s in str_list:
        if '.' in s:
            raise ValueError(f'. in {s}')


def are_all_scalars(str_list,scalar_variables):
    for s in str_list:
        if not s in scalar_variables:
            raise ValueError(f'Not a scalar: {s}')


def are_all_set_variables(str_list,set_variables):
    for s in str_list:
        if not s in set_variables:
            raise ValueError(f'Not a set variable: {s}')



class Vardef:
    def __init__(self):
        self.vars_inds_map = []
        self.targets = []
        self.args = []

    def format(self, var):
        return ast.Name(id=var.replace('scope.', 's_'))

    def var_def(self, var, read=True):
        if not var in self.vars_inds_map:
            self.vars_inds_map.append(var)
        if read and 'scope.' in var:
            if var not in self.targets and var not in self.args:
                self.args.append(var)
        elif 'scope.' in var:

            if var not in self.targets:
                self.targets.append(var)

        return self.format(var)

    def get_args(self, form=True):
        if form:
            return [self.format(a) for a in self.args]
        else:
            return self.args

    def get_targets(self, form=True):
        if form:
            return [self.format(a) for a in self.targets]
        else:
            return self.targets


class Vardef_llvm:
    def __init__(self):
        self.vars_inds_map = []
        self.targets = []
        self.args = []

    def format(self, var):
        return ast.Name(id=var.replace('scope.', 's_'))

    def format_target(self, var):
        return ast.Subscript(slice=ast.Index(value=ast.Num(n=0)), value=ast.Call(
            args=[ast.Name(id=var.replace('scope.', 's_')), ast.Tuple(elts=[ast.Num(n=1)])], func=ast.Name(id='carray'),
            keywords=[]))

    def var_def(self, var, read=True):
        if not var in self.vars_inds_map:
            self.vars_inds_map.append(var)
        if read and 'scope.' in var:
            if var not in self.targets and var not in self.args:
                self.args.append(var)
        elif 'scope.' in var:

            if var not in self.targets:
                self.targets.append(var)

        if var in self.targets:
            return self.format_target(var)
        else:
            return self.format(var)

    def get_args(self, form=True):
        if form:
            return [self.format(a) for a in self.args]
        else:
            return self.args

    def get_targets(self, form=True):
        if form:
            return [self.format(a) for a in self.targets]
        else:
            return self.targets