"""Download/assemble the OT recovery package using Python 3.12 standard library."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,urllib.request,zipfile,shutil
REPO='ot114514704/OT'
LOCATION='portable/2026-11-15'

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'OT-Recovery'})
    with urllib.request.urlopen(req,timeout=120) as r:return r.read()

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,default=Path.cwd()/'OT-Recovery-Package')
    p.add_argument('--offline',action='store_true',help='Use adjacent manifest and parts from GitHub Download ZIP')
    a=p.parse_args();dest=a.destination.resolve()
    if dest.exists():raise FileExistsError('Choose a new destination; no existing folder is replaced')
    here=Path(__file__).resolve().parent
    base=None
    if a.offline:manifest=json.loads((here/'download-manifest.json').read_text('utf-8'))
    else:
        commit=json.loads(get(f'https://api.github.com/repos/{REPO}/git/ref/heads/main'))['object']['sha']
        base=f'https://raw.githubusercontent.com/{REPO}/{commit}/{LOCATION}/'
        manifest=json.loads(get(base+'download-manifest.json'))
    # Parts are simple filenames, never URL paths or destinations supplied by a manifest.
    for item in manifest['parts']:
        if Path(item['file']).name!=item['file'] or '/' in item['file'] or '\\' in item['file']:
            raise ValueError('Invalid part name')
    cache=dest.with_name(dest.name+'-download');cache.mkdir(exist_ok=True)
    parts=[]
    for i,item in enumerate(manifest['parts'],1):
        name=item['file'];target=cache/name;local=here/'parts'/name
        if not target.exists() or sha(target)!=item['sha256']:
            if a.offline:shutil.copyfile(local,target)
            else:
                partial=target.with_suffix(target.suffix+'.partial')
                partial.write_bytes(get(base+'parts/'+name));partial.replace(target)
        if target.stat().st_size!=item['bytes'] or sha(target)!=item['sha256']:raise ValueError('Part hash mismatch: '+name)
        parts.append(target);print(f'Checked {i}/{len(manifest["parts"])}')
    archive=cache/'package.zip'
    with archive.open('wb') as out:
        for part in parts:
            with part.open('rb') as src:shutil.copyfileobj(src,out)
    if archive.stat().st_size!=manifest['bytes'] or sha(archive)!=manifest['sha256']:raise ValueError('Archive hash mismatch')
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            path=PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename:
                raise ValueError('Unsafe archive path')
        if z.testzip() is not None:raise ValueError('Corrupt archive')
        z.extractall(dest)
    internal=json.loads((dest/'MANIFEST.json').read_text('utf-8'))
    for name,expected in internal['files'].items():
        file=(dest/name).resolve()
        if not file.is_relative_to(dest) or sha(file)!=expected:raise ValueError('Extracted file mismatch: '+name)
    print('Verified package:',dest)
    print('Next: read README.md and run restore.py; no service or terminal was started.')
if __name__=='__main__':main()

