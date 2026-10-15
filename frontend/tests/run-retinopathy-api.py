"""Exercise the JS client against disposable FastAPI/SQLite/MongoDB with real models."""
import csv,json,os,secrets,shutil,socket,subprocess,sys,tempfile,time
from pathlib import Path
from pymongo import MongoClient
ROOT=Path(__file__).resolve().parents[2]
def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]
with tempfile.TemporaryDirectory(prefix='retino-step12-') as tmp:
    path=Path(tmp);(path/'mongo').mkdir();mongo_port=port();api_port=port()
    mongo=subprocess.Popen([shutil.which('mongod'),'--bind_ip','127.0.0.1','--port',str(mongo_port),'--dbpath',str(path/'mongo'),'--logpath',str(path/'mongo.log'),'--nounixsocket'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    server=None
    try:
        uri=f'mongodb://127.0.0.1:{mongo_port}'
        for _ in range(50):
            try:
                with MongoClient(uri,serverSelectionTimeoutMS=200) as client:client.admin.command('ping')
                break
            except Exception:time.sleep(.2)
        else:raise RuntimeError('Disposable MongoDB unavailable')
        env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'MONGODB_URI':'','JWT_SECRET':secrets.token_hex(32),'RETINOPATHY_MONGODB_URI':uri,'RETINOPATHY_MONGODB_DATABASE':'step12_disposable','RETINOPATHY_UPLOAD_DIR':str(path/'uploads'),'RETINOPATHY_OUTPUT_DIR':str(path/'outputs'),'RETINO_TEST_ROOT':tmp}
        code="""import os
from pathlib import Path
from app.api import auth
auth._users=None
auth._local_db=Path(os.environ['RETINO_TEST_ROOT'])/'auth.sqlite3'
import app.services.retinopathy_service as service
from app.services.retinopathy.private_storage import PrivateImageStore
service.PrivateImageStore=lambda:PrivateImageStore(Path(os.environ['RETINO_TEST_ROOT'])/'persistent')
from app.main import app
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=PORT,log_level='error')
""".replace('PORT',str(api_port))
        with (path/'server.log').open('w') as log:
            server=subprocess.Popen([sys.executable,'-c',code],env=env,stdout=log,stderr=log)
            import urllib.request
            for _ in range(100):
                try:urllib.request.urlopen(f'http://127.0.0.1:{api_port}/health',timeout=1);break
                except Exception:time.sleep(.2)
            else:raise RuntimeError('Disposable FastAPI unavailable')
            config=json.loads((ROOT/'ai-model/config/local.json').read_text())['aptos2019']
            with (ROOT/'ai-model/splits/aptos_test.csv').open() as f:sample=next(csv.DictReader(f))
            result=subprocess.run(['node',str(ROOT/'frontend/tests/retinopathy.real-api.mjs')],env={**env,'RETINO_DISPOSABLE_TEST':'1','NEXT_PUBLIC_API_URL':f'http://127.0.0.1:{api_port}','RETINO_FUNDUS_SAMPLE':str(Path(config['root'])/sample['relative_path'])})
            if result.returncode:raise RuntimeError('Real API client checks failed')
    finally:
        for process in (server,mongo):
            if process is not None:
                process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait()
