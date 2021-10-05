import time
import pyupbit
import datetime
import requests
import telegram
import pandas as pd
pd.set_option('mode.chained_assignment',  None)
access = "kz6RzMwD5wv6yGNfvx9gXpGVxsrxqFfxSbijx8qY"
secret = "3bm4LtCD1ISLFstfmsWJQxuMPbg7kd9j8KASJtXG"

TOKEN = '1919980133:AAG845Pwz1i4WCJvaaamRT-_QE0uezlvA9A'
ID = '1796318367'
bot = telegram.Bot(TOKEN)


def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma10(ticker):
    """10일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=10)
    ma15 = df['close'].rolling(10).mean().iloc[-1]
    return ma15

def get_balance(coin):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == coin:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

def get_hpr(k):

    dfs = []
    df= pyupbit.get_ohlcv("KRW-XRP",interval="day", count=30)
    dfs.append(df)

    df['range'] = (df['high']-df['low'])*k
    #target(매수가), range 컬럼을 한칸씩 밑으로 내림(.shift(1))
    df['target_price'] = round(df['open'] + df['range'].shift(1),-3)
    #다음날 시가
    df['tomorrow_open'] = df['open'].shift(-1)

    #10일 이평선
    df['ma10'] = df['close'].rolling(10).mean()
    #null 삭제 하기
    df=df[df['ma10'].notnull()]

    #조건 만족했는지 확인
    cond = ((df['high']>df['target_price']) & (df['high']>df['ma10']))
    #수익률
    df['ror'] = df.loc[cond,'tomorrow_open']/df.loc[cond,'target_price']
    #누적 수익률
    df['hpr'] = df['ror'].cumprod()
    df=df[df['hpr'].notnull()]
    df.loc[cond].to_excel("backtesting_k=%.1f.xlsx" %(k))
    result = df.iloc[-1]['hpr']
    return result

def find_best_k():
    ks = []
    k_list = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
    for k in k_list:
        hpr = get_hpr(k)
        ks.append(hpr)
    hpr = pd.DataFrame({"hpr": ks})
    k_data = pd.DataFrame({"k": k_list})
    sum = pd.concat([k_data, hpr], axis =1)
    final=sum.sort_values(by = "hpr", ascending=False)
    best_k = final.iloc[:10]['k'].values.tolist()[0]
    return best_k

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("XRPautotrade start")
# 시작 메세지 텔레그램 전송
bot.sendMessage(ID, "XRPautotrade start")

check_buy = False
check_inform = False
k = 0.1

while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-XRP")
        end_time = start_time + datetime.timedelta(days=1)

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            check_inform = False
            target_price = get_target_price("KRW-XRP", k)
            ma10 = get_ma10("KRW-XRP")
            current_price = get_current_price("KRW-XRP")
            if check_buy == False and target_price < current_price and ma10 < current_price:   
                krw = get_balance("KRW")
                real_target = round(target_price,-1)
                total = (krw*0.9995)/real_target
                if krw > 5000:
                    buy_result = upbit.buy_limit_order("KRW-XRP", real_target, total)
                    bot.sendMessage(ID, "T_XRP buy :"+str(buy_result))
                    check_buy = True

        else:
            btc = get_balance("XRP")
            if btc >= 5.0 and check_inform == False:
                sell_result = upbit.sell_market_order("KRW-XRP", btc*0.9995)
                bot.sendMessage(ID, "T_XRP sell :"+str(sell_result))
                check_buy = False
                check_inform = True
                k=find_best_k()
                bot.sendMessage(ID, "Today's k : "+str(k))
            elif btc < 5.0 and check_inform == False:
                uuid = buy_result['uuid']
                cancel_result = upbit.cancel_order(uuid)
                bot.sendMessage(ID, "T_XRP cancel :"+str(cancel_result))
                check_buy = False
                check_inform = True
                k=find_best_k()
                bot.sendMessage(ID, "Today's k : "+str(k))
        time.sleep(1)
    except Exception as e:
        print(e)
        bot.sendMessage(ID, e)
        time.sleep(1)
