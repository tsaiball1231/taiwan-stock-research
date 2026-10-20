#!/usr/bin/env python3
"""Fetch TWSE listed-stock daily quotes and write public JSON files."""
import json, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
LATEST=DATA/'latest.json'; HISTORY=DATA/'history.json'
URL='https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
TAIPEI=timezone(timedelta(hours=8)); WATCHLIST={'2330','2317','2454','0050','0056','00878','00919'}
def fetch():
    req=urllib.request.Request(URL,headers={'User-Agent':'TaiwanStockPlainLanguageLearningSite/1.0'})
    with urllib.request.urlopen(req,timeout=40) as r: data=json.loads(r.read().decode('utf-8-sig'))
    if not isinstance(data,list): raise RuntimeError('API response is not a JSON list; endpoint format may have changed.')
    return data
def get(row,*keys):
    for k in keys:
        if k in row:return row[k]
    return None
def num(v):
    if v is None:return None
    s=str(v).strip().replace(',','').replace('＋','+').replace('﹢','+')
    if s in ('','--','X','-','—','除權息','除息','除權'):return None
    try:return float(s)
    except ValueError:return None
def roc_date(v):
    if v is None:return None
    s=str(v).strip().replace('/','').replace('-','')
    if len(s)!=7 or not s.isdigit():return None
    return f'{int(s[:3])+1911:04d}-{s[3:5]}-{s[5:7]}'
def normalize(r):
    code=str(get(r,'Code','證券代號','股票代號') or '').strip(); name=str(get(r,'Name','證券名稱','股票名稱') or '').strip()
    if not code or not name:return None
    v=get(r,'TradeVolume','成交股數'); volume=num(v)
    return {'date':roc_date(get(r,'Date','日期','資料日期')),'code':code,'name':name,
      'open':num(get(r,'OpeningPrice','開盤價')),'high':num(get(r,'HighestPrice','最高價')),'low':num(get(r,'LowestPrice','最低價')),
      'close':num(get(r,'ClosingPrice','收盤價')),'change':num(get(r,'Change','漲跌價差')),
      'volume':int(volume) if volume is not None else None,'value':int(num(get(r,'TradeValue','成交金額'))) if num(get(r,'TradeValue','成交金額')) is not None else None,
      'transactions':int(num(get(r,'Transaction','成交筆數'))) if num(get(r,'Transaction','成交筆數')) is not None else None}
def read_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except (FileNotFoundError,json.JSONDecodeError):return default
def main():
    DATA.mkdir(parents=True,exist_ok=True); stocks=[s for s in (normalize(r) for r in fetch()) if s]
    dates=sorted({s['date'] for s in stocks if s['date']}); market_date=dates[-1] if dates else None
    if not market_date:raise RuntimeError('No valid market date found; refusing to publish.')
    if sum(s['close'] is not None for s in stocks)<100:raise RuntimeError('Too few valid closing prices; refusing to overwrite data.')
    updated=datetime.now(TAIPEI).isoformat(timespec='seconds')
    latest={'meta':{'market_date':market_date,'updated_at_taipei':updated,'source_name':'臺灣證券交易所 OpenAPI','source_url':URL,'row_count':len(stocks),'note':'交易日依 API 回傳日期判斷；休市或來源延遲時，資料日期可能不是今天。'},'stocks':sorted(stocks,key=lambda x:x['code'])}
    LATEST.write_text(json.dumps(latest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
   
    history = read_json(HISTORY, {'source': URL, 'days': []})
    by_date = {
        d.get('date'): d
        for d in history.get('days', [])
        if d.get('date')
    }

    by_date[market_date] = {
        'date': market_date,
        'stock_count': len(stocks),
        'advancers': sum(
            s['change'] is not None and s['change'] > 0
            for s in stocks
        ),
        'decliners': sum(
            s['change'] is not None and s['change'] < 0
            for s in stocks
        ),
        'stocks': {
            s['code']: {
                'name': s['name'],
                'close': s['close'],
                'change': s['change'],
                'volume': s['volume']
            }
            for s in stocks
        }
    }

    history['days'] = [
        by_date[d] for d in sorted(by_date)
    ][-60:]
    history['last_updated_taipei'] = updated

    HISTORY.write_text(
        json.dumps(history, ensure_ascii=False, separators=(',', ':')) + '\n',
        encoding='utf-8'
    )

    print(f'Saved {len(stocks)} stock rows for {market_date}; updated {updated}.')
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'ERROR: {e}',file=sys.stderr);raise
