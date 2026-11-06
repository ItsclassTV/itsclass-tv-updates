"""Publish football-data.org fixtures in ItsclassTV's football.json format.
Only competitions included in the API subscription will be returned.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

key = os.environ.get('FOOTBALL_API_KEY', '').strip()
if not key:
    raise SystemExit('Missing FOOTBALL_API_KEY secret')

uk = ZoneInfo('Europe/London')
today = datetime.now(uk).date()
# Include an extra day either side of the UK calendar day to avoid UTC date-boundary omissions.
params = urlencode({'dateFrom': (today - timedelta(days=1)).isoformat(),
                    'dateTo': (today + timedelta(days=1)).isoformat()})
url = 'https://api.football-data.org/v4/matches?' + params
req = Request(url, headers={'X-Auth-Token': key, 'Accept': 'application/json',
                            'User-Agent': 'ItsclassTV-Fixtures/1.0'})
try:
    with urlopen(req, timeout=30) as resp:
        data = json.load(resp)
except HTTPError as e:
    raise SystemExit(f'Football API returned HTTP {e.code}; check key, access and rate limits')
except (URLError, TimeoutError) as e:
    raise SystemExit(f'Football API unavailable: {e}')

fixtures = []
for match in data.get('matches', []):
    kickoff_raw = match.get('utcDate')
    if not kickoff_raw:
        continue
    try:
        kickoff = datetime.fromisoformat(kickoff_raw.replace('Z', '+00:00'))
    except ValueError:
        continue
    if kickoff.astimezone(uk).date() != today:
        continue
    home = (match.get('homeTeam') or {}).get('name')
    away = (match.get('awayTeam') or {}).get('name')
    if not home or not away:
        continue
    fixtures.append({
        'home': home,
        'away': away,
        'competition': (match.get('competition') or {}).get('name') or 'Football',
        'kickoffUtc': kickoff.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        # Broadcast rights are NOT supplied by football-data.org. Never invent channels.
        'ukChannels': []
    })
fixtures.sort(key=lambda m: (m['kickoffUtc'], m['competition'], m['home']))
output = {'fixtures': fixtures}
Path('football.json').write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'Published {len(fixtures)} matches for {today} (UK). API coverage may be incomplete.')
