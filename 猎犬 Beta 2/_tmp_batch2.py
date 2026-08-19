from hound_system.data.fetcher import HoundFetcher
import json

codes = ['600000','600004','600008','600009','600010','600011','600015','600016','600018','600019',
         '600021','600022','600023','600025','600026','600027','600028','600029','600030','600031',
         '600032','600036','600038','600039','600048','600050','600052','600056','600058','600060']

f = HoundFetcher()
results = {}
for code in codes:
    try:
        d = f.get_capital_evidence(code)
        results[code] = d
    except Exception as e:
        results[code] = {'error': str(e)}

with open('/tmp/capital_evidence_batch.json','w') as fh:
    json.dump(results, fh, ensure_ascii=False, default=str)
print('saved', len(results), 'stocks')
