"""Independently compare a saved H1 Book inspection with the local MT5 native history."""
import json
from datetime import datetime, timezone
import MetaTrader5 as mt
from inspect_current_book_structure import OUT, epoch, fetch, verified


def main():
    report=json.loads((OUT/'current_closed_book.json').read_text('utf8'))
    bars=report['source_rows']
    cutoff=epoch(report['chart_clock'])
    if not mt.initialize(path='C:/Program Files/MetaTrader 5/terminal64.exe',timeout=10000):
        raise RuntimeError(str(mt.last_error()))
    try:
        server=mt.account_info().server
        terminal=mt.terminal_info()
        assert terminal.connected and server==report['market_source']['server']
        last=mt.copy_rates_from_pos('XAUUSD',mt.TIMEFRAME_H1,0,1)
        assert last is not None and len(last)==1
        forming=int(last[0]['time'])
        native=mt.copy_rates_range('XAUUSD',mt.TIMEFRAME_H1,datetime.fromtimestamp(epoch(bars[0]['timestamp_utc']),timezone.utc),
                                   datetime.fromtimestamp(cutoff-1,timezone.utc))
        assert native is not None and len(native)==len(bars)
        for b,n in zip(bars,native):
            assert epoch(b['timestamp_utc'])==int(n['time'])<forming
            assert all(b[k]==float(n[k]) for k in ('open','high','low','close'))
    finally:
        mt.shutdown()
    state=fetch('live')
    result=dict(checked_bars=len(bars),clock=report['chart_clock'],native_forming_open=forming,
                same_market=server,all_native_ohlc_equal=True,
                latest_at_verification=(forming==cutoff and verified(state) and epoch(state['latest_closed_end']['H1'])==cutoff))
    (OUT/'mt5_history_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf8')
    print(result)

if __name__=='__main__':
    main()
