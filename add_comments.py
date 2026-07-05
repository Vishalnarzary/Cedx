import ast
import os

def generate_comment(name):
    clean = name.replace('_', ' ')
    if name.startswith('is_'):
        return f"Check if {clean[3:]}."
    elif name.startswith('has_'):
        return f"Check if it has {clean[4:]}."
    elif name.startswith('parse_'):
        return f"Parse {clean[6:]} from the given input."
    elif name.startswith('make_'):
        return f"Make and return {clean[5:]}."
    elif name.startswith('eval_'):
        return f"Evaluate {clean[5:]}."
    elif name.startswith('probe_'):
        return f"Run probe for {clean[6:]}."
    elif name.startswith('call_'):
        return f"Call {clean[5:]} API."
    elif name.startswith('get_'):
        return f"Get {clean[4:]}."
    elif name.startswith('set_'):
        return f"Set {clean[4:]}."
    else:
        return f"Execute {clean} operation."

with open('easy.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tree = ast.parse(''.join(lines))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
functions.sort(key=lambda x: x.lineno, reverse=True)

for f in functions:
    insert_idx = f.body[0].lineno - 1
    indent_str = lines[insert_idx][:len(lines[insert_idx]) - len(lines[insert_idx].lstrip())]
    comment_text = generate_comment(f.name)
    comment = f"{indent_str}# {comment_text}\n"
    lines.insert(insert_idx, comment)

with open('easy.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Comments added successfully.")
