#!/usr/bin/env python3
"""Lex Swift strings; print inventory or wrap Arabic UI strings. Does not alter interpolation code.
Run --apply only after concurrent Swift edits finish. Review the diff before packaging.
"""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AR=re.compile(r'[\u0600-\u06ff]')

def quoted(src,start):
    # Return string end, literal segments and interpolation expressions.
    triple=src.startswith('"""',start); delim='"""' if triple else '"'
    i=start+len(delim); parts=['']; args=[]
    while i<len(src):
        if src.startswith(delim,i): return i+len(delim),parts,args
        if src.startswith('\\(',i):
            j=i+2; begin=j; depth=1
            while j<len(src) and depth:
                if src[j]=='"': j=quoted(src,j)[0]; continue
                if src[j]=='(': depth+=1
                elif src[j]==')': depth-=1
                j+=1
            if depth: raise ValueError('Unclosed interpolation')
            args.append(src[begin:j-1]); parts.append(''); i=j; continue
        if src[i]=='\\' and i+1<len(src): parts[-1]+=src[i:i+2];i+=2;continue
        parts[-1]+=src[i];i+=1
    raise ValueError('Unclosed string')

def transform(src,apply=False):
    result=[]; keys=[]; i=0
    while i<len(src):
        if src.startswith('//',i):
            end=src.find('\n',i); end=len(src) if end<0 else end
            result.append(src[i:end]); i=end;continue
        if src.startswith('/*',i):
            end=src.find('*/',i+2);end=len(src) if end<0 else end+2
            result.append(src[i:end]);i=end;continue
        if src[i]!='"':result.append(src[i]);i+=1;continue
        end,parts,args=quoted(src,i); original=src[i:end]
        prefix=src[max(0,i-100):i]
        # Existing L keys and dictionary/catalog definitions are not double-wrapped.
        already=bool(re.search(r'\bL\(\s*$',prefix))
        enum_raw=bool(re.search(r'^\s*case\b[^\n]*=\s*$',src[src.rfind('\n',0,i)+1:i]))
        if AR.search(''.join(parts)) and not already and not enum_raw and not original.startswith('"""'):
            key=''.join(p+(('{'+str(n)+'}') if n<len(args) else '') for n,p in enumerate(parts))
            keys.append(key)
            localized_args=[]
            for argument in args:
                converted,nested=transform(argument,apply);localized_args.append(converted);keys.extend(nested)
            replacement='L("'+key+'"'+''.join(', '+a for a in localized_args)+')'
            result.append(replacement if apply else original)
        else: result.append(original)
        i=end
    return ''.join(result),keys

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--inventory',type=Path);parser.add_argument('--exclude',action='append',default=[]);args=parser.parse_args()
    keys=set()
    for path in sorted((ROOT/'macos/Sources/EISApp').glob('*.swift')):
        if path.name in {'Localization.swift','LocalizationCatalog.swift', *args.exclude}:continue
        transformed,found=transform(path.read_text(),args.apply);keys.update(found)
        if args.apply:
            # Register a language dependency without recreating stateful view identities.
            # Native App and NSViewRepresentable use their existing environment/update paths.
            transformed=re.sub(r'(struct\s+\w+(?:<[^\n]+>)?\s*:\s*View\s*\{)(?!\n    @AppStorage\("appLanguage"\))', r'\1\n    @AppStorage("appLanguage") private var interfaceLanguage = "ar"', transformed)
            transformed=re.sub(r'(var body:\s*some View\s*\{)(?!\n\s*let _ = interfaceLanguage)', r'\1\n        let _ = interfaceLanguage', transformed)
            transformed=re.sub(r'Text\((\w+\.rawValue)\)', r'Text(L(\1))', transformed)
            path.write_text(transformed)
    if args.inventory:args.inventory.write_text(json.dumps(sorted(keys),ensure_ascii=False,indent=2)+'\n')
    else:print(json.dumps(sorted(keys),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
