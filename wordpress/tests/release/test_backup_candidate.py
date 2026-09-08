"""The restore rehearsal builds a disposable fixture, never a release transport."""

import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SHA = 'a' * 40
IMAGE = 'sha256:' + 'b' * 64


class BackupCandidateTest(unittest.TestCase):
    def test_actual_restore_consumer_builds_and_parses_fixture_before_deploy(self):
        for outcome in ('valid', 'build-failure', 'invalid-image'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                wp = root/'wordpress'
                for name in ('bin', 'tests', 'runtime'):
                    (wp/name).mkdir(parents=True)
                tools = root/'tools'
                tools.mkdir()
                log = root/'calls.jsonl'
                shutil.copyfile(ROOT/'wordpress/tests/backup-restore-runtime.sh', wp/'tests/backup-restore-runtime.sh')
                # Retain the real obsolete entry point for a genuine RED on old callers.
                (wp/'bin/build-release').write_text('#!/usr/bin/env bash\nexec '+shlex.quote(str(ROOT/'wordpress/bin/build-release'))+' "$@"\n')
                (wp/'bin/build-release').chmod(0o700)
                (tools/'git').write_text('#!/usr/bin/env python3\nimport sys\nassert sys.argv[1:] == '+repr(['-C', str(wp/'..'), 'rev-parse', 'HEAD'])+'\nprint('+repr(SHA)+')\n')
                (tools/'docker').write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
a=sys.argv[1:]; root=Path(os.environ['FIXTURE_ROOT']); wp=root/'wordpress'
with (root/'calls.jsonl').open('a') as f: f.write(json.dumps(['docker']+a)+'\\n')
if a and a[0]=='build':
    i=a.index('--iidfile'); target=Path(a[i+1])
    assert target.is_absolute() and target.parent.parent == root
    assert a[:i]+['--iidfile','<path>']+a[i+2:] == [
        'build','--platform','linux/amd64','--file',str(wp/'runtime/Dockerfile'),
        '--build-arg','GAMA_GIT_SHA='+('a'*40),
        '--build-arg','GAMA_RELEASE_MARKER=backup-restore-fixture',
        '--iidfile','<path>',str(wp/'..')]
    if os.environ['BUILD_OUTCOME']=='build-failure': raise SystemExit(23)
    target.write_text('invalid' if os.environ['BUILD_OUTCOME']=='invalid-image' else 'sha256:'+('b'*64)+'\\n')
elif a[:2]==['compose','--project-name'] and a[2].startswith(('gama-wp-staging-backup-','gama-restore-')) and a[-3:]==['down','--volumes','--remove-orphans']:
    pass
else: raise SystemExit('unexpected Docker boundary: '+repr(a))
''')
                (wp/'bin/deploy-staging').write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
a=sys.argv[1:]
assert len(a)==5 and a[0]=='--project' and a[1].startswith('gama-wp-staging-backup-') and a[2]=='--env-file' and a[4]=='--confirm'
values=Path(a[3]).read_text().splitlines()
with (Path(os.environ['FIXTURE_ROOT'])/'calls.jsonl').open('a') as f:
    f.write(json.dumps(['deployment-boundary',next(x for x in values if x.startswith('WORDPRESS_IMAGE='))])+'\\n')
raise SystemExit(73)
''')
                for path in (tools/'git', tools/'docker', wp/'bin/deploy-staging'):
                    path.chmod(0o700)
                env = dict(os.environ, PATH=str(tools)+os.pathsep+os.environ['PATH'],
                           TMPDIR=str(root), FIXTURE_ROOT=str(root), BUILD_OUTCOME=outcome)
                result = subprocess.run(['bash', str(wp/'tests/backup-restore-runtime.sh')],
                                        env=env, capture_output=True, text=True, timeout=15)
                calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
                self.assertEqual(1, sum(call[:2] == ['docker', 'build'] for call in calls), result.stderr)
                if outcome == 'valid':
                    self.assertEqual(73, result.returncode, result.stderr)
                    self.assertIn(['deployment-boundary', 'WORDPRESS_IMAGE='+IMAGE], calls)
                else:
                    self.assertEqual(23 if outcome == 'build-failure' else 1, result.returncode, result.stderr)
                    self.assertFalse(any(call[0] == 'deployment-boundary' for call in calls), calls)
