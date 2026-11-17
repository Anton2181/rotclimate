"""Retrieve only the declared primary book page;register exposure before any body."""
import datetime
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_columella_calendar_20261117'
PARENT=ROOT/'output/urban_work_evidence_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/columella_calendar_source.json'
URL='https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/11%2A.html'


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    q=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in q[key].items():assert sha(prefix/name)==digest,name
    OUT.mkdir(exist_ok=True);source=OUT/'source';source.mkdir(exist_ok=True)
    if not (OUT/'exposure.json').exists():
        write(OUT/'exposure.json',dict(status='registered_development_before_calendar_body_fetch',plan_sha256=sha(PLAN),
            target='Columella,De re rustica11.2',registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            retrieval_scope='BookXI English page;chapter2 only analytic;other chapters/notes possibly incidental retrieval',
            prospective_Latin_scope='Same book/chapter only after linked identity check',source_is_development=True,
            independent_validation_cohort=False,reserved_pools_or_workbook_opened=False,model_parameter_adoption=False))
    assert read(OUT/'exposure.json')['plan_sha256']==sha(PLAN)
    target=source/'book11_english.html';assert not target.exists(),'Preserve fetched source bytes'
    request=urllib.request.Request(URL,headers={'User-Agent':'rotclimate source research/1.0'})
    try:
        with urllib.request.urlopen(request,timeout=30) as response:
            body=response.read();final=response.url;headers=dict(response.headers);status=response.status
    except urllib.error.HTTPError as error:
        (source/'english_http_error.html').write_bytes(error.read())
        write(OUT/'retrieval_failure.json',dict(status='preserved_primary_calendar_access_failure',url=URL,http_status=error.code,
            fetcher_sha256=sha(Path(__file__)),challenge_bypass_attempted=False));raise
    target.write_bytes(body)
    write(OUT/'retrieval.json',dict(status='primary_page_retrieved_identity_not_yet_checked',requested_url=URL,final_url=final,
        fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),http_status=status,bytes=len(body),sha256=sha(target),
        content_type=headers.get('Content-Type'),source_path=str(target.relative_to(OUT)),fetcher_sha256=sha(Path(__file__)),
        plan_sha256=sha(PLAN),challenge_bypass_attempted=False))
    print(status,len(body),'bytes',sha(target),flush=True)


if __name__=='__main__':main()
