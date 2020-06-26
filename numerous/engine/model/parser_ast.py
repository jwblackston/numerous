import inspect
from enum import IntEnum, unique
import ast#, astor
from textwrap import dedent
from numerous.engine.model.graph import Graph

op_sym_map = {ast.Add: '+', ast.Sub: '-', ast.Div: '/', ast.Mult: '*', ast.Pow: '**', ast.USub: '*-1'}

def get_op_sym(op):
    return op_sym_map[type(op)]

@unique
class NodeTypes(IntEnum):
    OP=0
    VAR=1
    ASSIGN=2

def attr_ast(attr):
    attr_ = attr.split('.')
    # print(attr_)
    if len(attr_) >1:
        prev = None
        attr_str = attr_[-1]
        attr_=attr_[:-1]
        for a in attr_:
            if not prev:
                prev = ast.Name(id=a)
            else:
                prev = ast.Attribute(attr=a, value=prev)

        attr_ast = ast.Attribute(attr=attr_str, value=prev)
    else:
        # print('attr_[0]')
        # print(attr_[0])
        attr_ast = ast.Name(id=attr_[0])
    return attr_ast

def recurse_Attribute(attr, sep='.'):
    if hasattr(attr,'id'):
        return attr.id
    elif isinstance(attr.value,ast.Name):
        return attr.value.id+sep+attr.attr
    elif isinstance(attr.value, ast.Attribute):
        return recurse_Attribute(attr.value)+sep+attr.attr
# Parse a function

# Add nodes and edges to a graph
tmp_count = [0]
def tmp(a):
    a+='_'+str(tmp_count[0])
    tmp_count[0]+=1
    return a

ass_count = [0]
def ass(a):
    a+='_'+str(ass_count[0])
    ass_count[0]+=1
    return a

class EquationNode:
    def __init__(self, label, id=None, ast_type=None, node_type:NodeTypes=NodeTypes.VAR, scope_var=None,**attrs):
        if not id:
            id = tmp(label)
        self.id = id
        self.label = label
        self.ast_type = ast_type
        self.scope_var=scope_var

        for k, v in attrs.items():
            setattr(self, k, v)

    def __str__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

class EquationEdge:
    def __init__(self, label, start: str = None, end: str = None):
        self.label = label
        self.start = start
        self.end = end

    def set_start(self, node_id: str):
        self.start = node_id

    def set_end(self, node_id: str):
        self.end = node_id


def parse_(ao, g: Graph, tag_vars, prefix='_', parent: EquationEdge=None):
    # print(ao)
    en=None

    if isinstance(ao, ast.Module):
        for b in ao.body:

            # Check if function def
            if isinstance(b, ast.FunctionDef):
                # Get name of function


                # Parse function
                for b_ in b.body:

                    parse_(b_, g, tag_vars, prefix)

    elif isinstance(ao, ast.Assign):

        assert len(ao.targets) == 1, 'Can only parse assignments with one target'

        target = ao.targets[0]

        # Check if attribute
        if isinstance(ao.targets[0], ast.Attribute) or isinstance(ao.targets[0], ast.Name):

            att = recurse_Attribute(ao.targets[0])
            # print(att)
            target_id = att

        else:
            raise AttributeError('Unknown type of target: ', type(ao.targets[0]))

        target_edge = EquationEdge(label='target0')
        value_edge = EquationEdge(label='value')

        en = EquationNode(label='=', ast_type=ast.Assign, node_type=NodeTypes.ASSIGN)
        target_edge.start = en.id
        value_edge.end = en.id




        g.add_edge((target_edge.start, target_edge.end, target_edge), ignore_missing_nodes=True)
        g.add_edge((value_edge.start, value_edge.end, value_edge), ignore_missing_nodes=True)

        parse_(ao.value, g, tag_vars,prefix, parent=value_edge.set_start)
        parse_(ao.targets[0], g, tag_vars, prefix, parent=target_edge.set_end)

    elif isinstance(ao, ast.Num):
        # Constant
        #source_var = Variable('c' + str(ao.value), Variable.CONSTANT, val=ao.value)
        source_id = 'c' + str(ao.value)
        en = EquationNode(id=source_id, value = ao.value, node_type=NodeTypes.VAR)


        # Check if simple name
    elif isinstance(ao, ast.Name) or isinstance(ao, ast.Attribute):
        local_id = recurse_Attribute(ao)
        source_id = local_id
        if source_id[:6]=='scope.':
            scope_var = tag_vars[source_id[6:]]
            #print('scope var: ',scope_var.id)
        else:
            scope_var=None
        en = EquationNode(id=source_id, local_id=local_id, ast_type=type(ao), label=source_id, node_type=NodeTypes.VAR, scope_var=scope_var)


    elif isinstance(ao, ast.UnaryOp):
        # Unary op
        op_sym = get_op_sym(ao.op)
        operand_edge = EquationEdge(label='operand')
        en = EquationNode(label = ''+op_sym, ast_type=ast.UnaryOp, node_type=NodeTypes.OP, ast_op=ao.op)
        operand_edge.end = en.id

        g.add_edge((operand_edge.start, operand_edge.end, operand_edge), ignore_missing_nodes=True)

        parse_(ao.operand, g, tag_vars, prefix, parent=operand_edge.set_start)

    elif isinstance(ao, ast.Call):


        op_name = recurse_Attribute(ao.func, sep='.')

        en = EquationNode(label=''+op_name, func=ao.func, ast_type=ast.Call, node_type=NodeTypes.OP)



        for i, sa in enumerate(ao.args):
            edge_i = EquationEdge(end=en.id, label=f'args{i}')

            parse_(ao.args[i], g, tag_vars, prefix=prefix, parent=edge_i.set_start)
            g.add_edge((edge_i.start, edge_i.end, edge_i), ignore_missing_nodes=True)


    elif isinstance(ao, ast.BinOp):

        op_sym = get_op_sym(ao.op) # astor.get_op_symbol(ao.op)
        en = EquationNode(label=''+op_sym, left=None, right=None, ast_type=ast.BinOp, node_type=NodeTypes.OP, ast_op=ao.op)

        for a in ['left', 'right']:

            operand_edge = EquationEdge(end=en.id, label=a)

            g.add_edge((operand_edge.start, operand_edge.end, operand_edge), ignore_missing_nodes=True)
            setattr(en,a,operand_edge)
            parse_(getattr(ao, a), g, tag_vars, prefix, parent=operand_edge.set_start)



    else:
        raise TypeError('Cannot parse <' + str(type(ao)) + '>')

    if en:
        g.add_node((en.id, en, None), ignore_exist=True)

    if parent:

        parent(en.id)

def qualify(s, prefix):
    return prefix + '_' + s.replace('scope.', '')

def qualify_equation(prefix, g, tag_vars):
    def q(s):
        return qualify(s, prefix)

    g_qual = Graph()
    g_qual.set_node_map({q(n[0]): (q(n[0]), n[1], (tag_vars[n[1].scope_var.tag].id if n[1].scope_var else None)) for nid, n in g.nodes_map.items()})

    for e in g.edges:
        g_qual.add_edge((q(e[2].start),q(e[2].end), EquationEdge(start=q(e[2].start), end=q(e[2].end), label=e[2].label)))

    return g_qual

parsed_eq = {}

def parse_eq(scope_id, item, global_graph, tag_vars):
    #print(item)
    for eq in item[0]:

        #dont now how Kosher this is: https://stackoverflow.com/questions/20059011/check-if-two-python-functions-are-equal
        eq_key = eq.__qualname__
        #print(eq_key)



        if not eq_key in parsed_eq:

            source = inspect.getsource(eq)
            #print(source)
            ast_tree = ast.parse(dedent(source))
            g = Graph()
            parse_(ast_tree, g, tag_vars)
            #g.as_graphviz()
            parsed_eq[eq_key] = (eq, source, g)
        else:
            pass
            #print('skip parsing')

        g = parsed_eq[eq_key][2]
        #print('qualify with ',scope_id)
        g_qualified = qualify_equation(scope_id, g, tag_vars)

        global_graph.update(g_qualified)

def process_mappings(mappings,gg:Graph, scope_vars, scope_map):

    for m in mappings:
        target_var = scope_vars[m[0]]
        #prefix = scope_map[target_var.parent_scope_id]
        prefix = f's{scope_map.index(target_var.parent_scope_id)}'
        target_var_id = qualify(target_var.tag, prefix)
        assign = EquationNode(label='=', ast_type=ast.Assign, node_type=NodeTypes.ASSIGN, targets=[], value=None)
        gg.add_node((assign.id, assign, None))
        target_node = EquationNode(id=target_var_id, label=target_var.tag, ast_type=ast.Attribute(attr_ast(m[0])), node_type=NodeTypes.VAR)
        gg.add_node((target_node.id, target_node, target_var.id), ignore_exist=True)
        gg.add_edge((assign.id, target_node.id, EquationEdge(start=assign.id, end=target_node.id, label='target0')))
        

        add = ast.Add()
        prev = None


        for i in m[1]:
            ivar_var = scope_vars[i]
            prefix = f's{scope_map.index(ivar_var.parent_scope_id)}'
            ivar_id = qualify(ivar_var.tag, prefix)
            ivar = EquationNode(id=ivar_id, label=ivar_var.tag, ast_type=ast.Attribute(attr_ast(i)), node_type=NodeTypes.VAR)
            gg.add_node((ivar.id, ivar, ivar_var.id, ), ignore_exist=True)

            if prev:
                binop = EquationNode(label=get_op_sym(add), ast_type=ast.BinOp, node_type=NodeTypes.OP, op=add)
                gg.add_node((binop.id, binop, None,))
                gg.add_edge((prev.id, binop.id, EquationEdge(start=prev.id, end=binop.id,label='left')))
                gg.add_edge((ivar.id, binop.id, EquationEdge(start=ivar.id, end=binop.id,labe='right')))
                prev = binop
            else:
                prev = ivar

        gg.add_edge((prev.id, assign.id, EquationEdge(start=prev.id, end=assign.id, label='value')))

        #ast.Assign(targets=ast.Attribute(attr_ast(m[0])), value = None)




