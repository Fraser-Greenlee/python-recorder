from typing import List
from random import randint, random, sample
from copy import deepcopy
from string import ascii_letters
import ast


from utils import TimeoutError, timeout


class AlternativeList(ast.NodeTransformer):
    def __init__(self):
        self.n_changes = 0
        super().__init__()

    def visit_List(self, node: List):
        code = ast.unparse(node)
        try:
            list_val = eval(code)
        except Exception:
            return node

        for _ in range(randint(0, 3)):
            list_val.append(randint(-999, 999))

        if not list_val:
            list_val.append(randint(-999, 999))

        list_val = sample(list_val, randint(1, len(list_val)))

        self.n_changes += 1
        return ast.parse(str(list_val)).body[0].value


class AlternativeConstant(ast.NodeTransformer):
    def __init__(self):
        self.n_changes = 0
        super().__init__()

    def visit_Constant(self, node):
        '''
            Switch constant values to simple variations
        '''
        if type(node.value) is int:
            if randint(0, 1) == 1:
                node.value = randint(-9, 9)
            else:
                node.value = randint(-999, 999)
        elif type(node.value) is str:
            if randint(0, 1) == 1 and node.value:
                if node.value:
                    node.value = ''.join(sample(node.value, randint(1, len(node.value))))
                else:
                    self.n_changes -= 1
            else:
                node.value = ''.join(sample(ascii_letters, randint(1, 4)))
        elif type(node.value) is float:
            if randint(0, 1) == 1:
                node.value = random()
            else:
                node.value = random() * randint(-999, 999)
        elif type(node.value) is bool:
            node.value = bool(randint(0, 1))
        else:
            self.n_changes -= 1
        self.n_changes += 1
        return super().visit_Constant(node)


class AlternativeNames(ast.NodeTransformer):

    def visit_Name(self, node):
        return ast.copy_location(ast.Subscript(
            value=ast.Name(id='data', ctx=ast.Load()),
            slice=ast.Index(value=ast.Str(s=node.id)),
            ctx=node.ctx
        ), node)


def state_dict_to_str(state):
    vals = []
    for k, v in state.items():
        vals.append(
            f'{k} = {v}'
        )
    vals = sorted(vals)
    return ';'.join(vals)


@timeout(seconds=3)
def trace_code(start_state: str, code: str):
    state = {}
    try:
        exec(start_state, {}, state)
    except Exception:
        return
    start_state = dict(state)
    try:
        exec(code, {}, state)
    except Exception:
        return
    return state_dict_to_str(start_state), code, state_dict_to_str(state)


def make_alternative_rows(start, code):
    variations = {}
    n_tries = 0
    state_root = ast.parse(start)

    while len(variations) < 10 and n_tries < 20:

        alt_state_root = None

        node_transformer = AlternativeList()
        try:
            alt_state_root = node_transformer.visit(deepcopy(state_root))
        except Exception:
            pass

        if node_transformer.n_changes < 1:
            node_transformer = AlternativeConstant()
            try:
                alt_state_root = node_transformer.visit(deepcopy(alt_state_root))
            except Exception:
                pass
            if node_transformer.n_changes < 1:
                n_tries += 10

        if alt_state_root:
            alt_start = ast.unparse(alt_state_root)
            try:
                alt_start_code_end = trace_code(alt_start, code)
                if alt_start_code_end:
                    variations[alt_start] = alt_start_code_end
            except TimeoutError:
                pass

        n_tries += 1

    # TODO change the names (keep alphabetical order)
    '''
    get number of vals in start states (N)
    get N random lowercase letters in alphabetical order
    parse start state and shuffle the expr.body
    make name map old->new using new characters
    use visitor with name map to swap variable names using map
        do this for start, code, end seperately
    '''
    return [
        {'start': st, 'code': cd, 'end': en} for st, cd, en in variations.values()
    ]


def lambda_handler(event, context):
    results = make_alternative_rows(context['start'], context['end'])
    return results
