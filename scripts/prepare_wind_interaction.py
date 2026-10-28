"""Prepare a prospective wind/rain interaction after completed broader exploration.

Only runs if no candidate is ready for broader validation. No climate is run.
"""
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json,identity
from tradeoff_search import diverse_starts


def prepare(parent,target):
    protocol=json.loads((parent/'protocol.json').read_text());review=json.loads((parent/'review.json').read_text());progress=json.loads((parent/'progress.json').read_text())
    if not review['complete'] or not progress['complete'] or review['identity']!=identity(protocol):raise ValueError('Complete and verify the parent first')
    if review['validation_shortlist']:raise ValueError('Broader validation takes priority; wind interaction is deferred')
    verification=json.loads((parent/'scientific_verification.json').read_text())
    if verification['status']!='passed' or verification['review_sha256']!=file_hash(parent/'review.json'):raise ValueError('Parent needs matching scientific verification')
    p=json.loads(json.dumps(protocol['plan']));updates={r['name']:r['updates'] for r in progress['records']}
    selection=dict(p['design'],local_starts=3,start_minimum_distance=.35)
    anchors=diverse_starts(review['scores'],updates,selection)
    if not anchors:raise ValueError('No admissible parent rain setting')
    parent_relative=str(parent.relative_to(ROOT));winds=[4.5,6.,8.5]
    parent_commit=subprocess.check_output(['git','log','-1','--format=%H','--',parent_relative+'/review.json'],cwd=ROOT,text=True).strip()
    if not parent_commit:raise ValueError('Commit completed parent results before declaring the follow-up')
    p['profiles']={n:protocol['plan']['profiles'][n] for n in p['control_names']}
    p['profile_numerics']={n:protocol['plan']['profile_numerics'][n] for n in p['control_names']}
    p['profile_control_archives']={n:parent_relative+'/'+n for n in p['control_names']}
    p['design']['bounds']['westerly_speed']={'range':[4.5,8.5],'scale':'linear'}
    p['design'].update(sampler='paired wind bracket',local_starts=1,local_poll_order=[],
        local_rule='No local refinement in this small interaction study; empty poll order. Common runner records the best point only; it proposes no local trials.')
    p['fixed_model'].pop('westerly_speed',None)
    p['global_names']=[];grid=[]
    for basin,anchor in enumerate(anchors):
        alias='source_anchor'+str(basin+1)
        # These archive bindings freeze source rows/arrays; aliases are not jobs.
        p['profile_control_archives'][alias]=parent_relative+'/'+anchor
        for wind in winds:
            name=f'global{len(grid)+1:02}';coeff={**updates[anchor],'westerly_speed':wind}
            p['profiles'][name]=coeff;p['profile_numerics'][name]=p['candidate_numerics'];p['global_names'].append(name)
            grid.append(dict(name=name,basin=basin+1,parent_profile=anchor,westerly_speed=wind))
    p['eligible_profiles']=p['global_names'];p['parent_protocol']=parent_relative+'/protocol.json';p['parent']=parent_relative+'/review.json'
    p['parent_source_commit']=parent_commit
    p['purpose']='Follow-up only when the completed broad rain search has no broader-validation shortlist. Test interaction of three separated fitted rain settings with the globally shared background westerly amplitude, motivated by retained native circulation errors. No regional coefficient, planetary retune or altered accuracy weights.'
    p['policy_version']='tradeoff_research_v1_wind_interaction_20261028'
    p['physical_definition']='Allow only the three parent shared storm/rain coefficients and westerly_speed to differ from the environmental control. Preserve environmental6K/km, independent water, corrected rain/recycling and every other actual parameter. Wind is background peak amplitude, not measured column speed; all coupled fields respond. Same hard invariant and reference checks, identical soft prediction objective and shortlist criteria.'
    p['screen']=protocol['plan']['screen'];p['advance']='This is a fixed small paired interaction bracket, not a global four-dimensional optimization. No adaptive extension and no local polish. Any shortlist still requires separately frozen broader Earth validation and world qualification before adoption.'
    p['publication']='All fixed wind/rain combinations, original7.5m/s parent anchors, numerical failures and all skill components. Source aliases are frozen archived comparisons, not new integrations. Preserve parent global-search outcomes; no automatic climate adoption.'
    p['publication_stem']='wind_interaction';p['planned_maximum_integrations']=(4+len(grid))*len(p['regions'])
    p['wind_interaction']=dict(parent=parent_relative,parent_identity=review['identity'],parent_review_sha256=file_hash(parent/'review.json'),
        parent_progress_sha256=file_hash(parent/'progress.json'),parent_verification_sha256=file_hash(parent/'scientific_verification.json'),
        anchor_selection=selection,anchors=anchors,winds_ms=winds,grid=grid,
        scope='Best separated parent rain settings; a conditional interaction test, not new independent validation or a global optimum.')
    p['generator_sha256']=file_hash(Path(__file__))
    if target.exists():raise ValueError('Preserve existing declaration; choose a fresh plan')
    target.parent.mkdir(parents=True,exist_ok=True);write_json(target,p)
    print(json.dumps(dict(plan=str(target),anchors=anchors,candidate_profiles=len(grid),maximum_integrations=p['planned_maximum_integrations']),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--parent',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True)
    a=ap.parse_args();prepare(a.parent.resolve(),a.plan.resolve())
