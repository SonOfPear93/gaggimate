import re
def parse(s):
    tok=re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
    stack=[[]]
    for m in tok.finditer(s):
        t=m.group(0)
        if t=='(':
            stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        else:
            if t[0]=='"': t=Str(t[1:-1].replace('\\"','"').replace('\\\\','\\'))
            stack[-1].append(t)
    return stack[0]
class Str(str): pass
def dump(x,ind=0):
    if isinstance(x,list):
        if not x: return '()'
        simple=all(not isinstance(e,list) for e in x)
        if simple: return '('+' '.join(dump(e) for e in x)+')'
        out='('+dump(x[0])
        for e in x[1:]:
            out+='\n'+'\t'*(ind+1)+dump(e,ind+1)
        return out+'\n'+'\t'*ind+')'
    if isinstance(x,Str): return '"'+x.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
    return str(x)
def find(x,key):
    return [e for e in x if isinstance(e,list) and e and e[0]==key]
def find1(x,key):
    r=find(x,key); return r[0] if r else None
