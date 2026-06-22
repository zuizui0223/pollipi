import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..');

function gitCommit() {
  try {
    return execFileSync('git', ['rev-parse', '--short=12', 'HEAD'], {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return 'unknown';
  }
}

function gitTimestamp() {
  try {
    return execFileSync('git', ['show', '-s', '--format=%cI', 'HEAD'], {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch {
    return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  }
}

const commit = gitCommit();
const timestamp = gitTimestamp();
const buildId = `${commit}-${timestamp.replace(/[-:]/g, '').replace('T', '-').replace(/\+.*/, '').replace('Z', '')}`;
const payload = {
  web_build_id: buildId,
  git_commit: commit,
  build_timestamp: timestamp,
};

const publicPath = join(repoRoot, 'packages', 'web', 'public', 'build-info.json');
mkdirSync(dirname(publicPath), { recursive: true });
writeFileSync(publicPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
console.log(`web_build_id=${buildId}`);
