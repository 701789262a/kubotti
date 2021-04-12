import binascii
import hashlib
import hmac
import json
import queue
import time
from threading import Thread

import binance
import krakenex
import pandas as pd
import requests
from binance import exceptions
from binance.client import Client
from colorama import Fore
from colorama import Style
from pykrakenapi import KrakenAPI

q1 = queue.Queue()
q2 = queue.Queue()
q3 = queue.Queue()


def create_sha256_signature(key, message):
    byte_key = binascii.unhexlify(key)
    message = message.encode()
    return hmac.new(byte_key, message, hashlib.sha256).hexdigest().upper()


class Operation:
    def __init__(self, exchange_list, apikey_trt=None, secret_trt=None, apikey_krk=None, secret_krk=None,
                 apikey_bnb=None, secret_bnb=None, pair="BTCEUR"):
        self.apikey_trt = apikey_trt
        self.secret_trt = secret_trt
        self.apikey_krk = apikey_krk
        self.secret_krk = secret_krk
        self.apikey_bnb = apikey_bnb
        self.secret_bnb = secret_bnb
        self.exchange_list = exchange_list
        self.client = Client(self.apikey_bnb, self.secret_bnb)
        self.trt = []
        self.prtrt = []
        self.bnb = []
        self.prbnb = []
        self.len = 0
        self.pair = pair

    def thread_func(self):
        while (1):
            if len(self.prtrt) < 20000:
                tr = Thread(target=lambda q, arg1, arg2: q.put(self.query(arg1, arg2)),
                            args=(q1, "trt",self.pair))
                self.prtrt.append(tr)
                bn = Thread(target=lambda q, arg1, arg2: q.put(self.query(arg1, arg2)),
                            args=(q2, "bnb", self.pair))
                self.prbnb.append(bn)
            else:
                time.sleep(1)
                if len(self.trt) < 25:
                    self.bnb = self.bnb + self.prbnb
                    self.trt = self.trt + self.prtrt
                    self.prtrt.clear()
                    self.prbnb.clear()
                    time.sleep(30)

    def threadCreation(self):
        x = Thread(target=self.thread_func)
        x.start()

    def trade(self, exchange, fund_id, side, amount, price):
        nonce = str(int(time.time() * 1e6))
        print(amount)
        amount = round(amount, 8)
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/" + fund_id + "/orders"
            payload_trt = {"fund_id": "BTCEUR", "side": side, "amount": amount, "price": 0}
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()

            _headers = {'User-Agent': 'PyRock v1', "Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.post(url, data=json.dumps(payload_trt), headers=_headers)
            try:
                return json.loads(resp.text)
            except KeyError:
                return "ERROR"
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = k.add_standard_order(fund_id, side, "limit", str(amount), str(price))
            resp = str(resp).replace("\'", "\"")
            return resp
        elif exchange == "bnb":

            if side == "buy":
                order = self.client.order_limit_buy(
                    symbol=fund_id,
                    quantity=round(amount, 8),
                    price=price
                )
            elif side == "sell":
                order = self.client.order_limit_sell(
                    symbol=fund_id,
                    quantity=round(amount, 8),
                    price=price
                )
            return dict(order)

    def __balance(self, exchange):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":

            url = "https://api.therocktrading.com/v1/balances"
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.get(url, headers=_headers)
            d["trtbtc"] = json.loads(resp.text)["balances"][0]["balance"]
            d["trteur"] = json.loads(resp.text)["balances"][8]["balance"]
            return d
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = k.get_account_balance()
            d["krkbtc"] = resp["vol"]["XXBT"]
            d["krkbch"] = resp["vol"]["BCH"]
            return d
        elif exchange == "bnb":
            is_fine = True
            while is_fine:
                try:
                    is_fine = False
                except ConnectionError:
                    print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
            try:
                d["bnbtrx"] = float(self.client.get_asset_balance(asset="TRX")["free"])
                d["bnbbnb"] = float(self.client.get_asset_balance(asset="BNB")["free"])
            except Exception:
                d["bnbtrx"] = float(self.client.get_asset_balance(asset="TRX")["free"])
                d["bnbbnb"] = float(self.client.get_asset_balance(asset="BNB")["free"])
            return d

    def balancethreading(self):
        d = dict()
        if "krk" in self.exchange_list:
            krk_balance = Thread(target=lambda q, arg1: q.put(
                self.__balance(arg1)),
                                 args=(q2, "krk"))
            krk_balance.start()
        if "trt" in self.exchange_list:
            trt_balance = Thread(target=lambda q, arg1: q.put(
                self.__balance(arg1)),
                                 args=(q1, "trt"))
            trt_balance.start()
        if "bnb" in self.exchange_list:
            bnb_balance = Thread(target=lambda q, arg1: q.put(
                self.__balance(arg1)),
                                 args=(q2, "bnb"))
            bnb_balance.start()
        try:
            trt_balance.join()
            d.update(q1.get())
        except:
            pass
        try:
            krk_balance.join()
            d.update(q2.get())
        except:
            pass
        try:
            bnb_balance.join()
            d.update(q2.get())
        except:
            pass
        return d

    def orderthreading(self, order1, order2=None):
        d = dict()
        bnb_order = Thread(target=lambda q, arg1, arg2: q.put(
            self.__order(arg1, arg2)),args=(q3, "bnb", order1))
        bnb_order.start()
        try:
            bnb_order.join()

            d.update(q3.get())
        except Exception:
            pass
        return d

    def cancel(self, order):
        self.client.cancel_order(symbol="TRXBNB", orderId=order)

    def __order(self, exchange, order):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        resp = self.client.get_order(symbol="TRXBNB", orderId=order)
        print("binance", resp)
        d["status_bnb"] = resp["status"]
        return d

    def __fee(self, exchange):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/BTCEUR"
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.get(url, headers=_headers)
            d["feetrttaker"] = json.loads(resp.text)["buy_fee"]
            d["feetrtmaker"] = json.loads(resp.text)["sell_fee"]

            return d
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = pd.DataFrame(k.get_trade_volume("BTCEUR")[2])
            d["feekrk"] = resp["XXBTZEUR"][0]
            return d
        elif exchange == "bnb":
            resp = self.client.get_trade_fee(symbol="BNBTRX")
            print(resp)
            d["feebnbtaker"] = resp["tradeFee"][0]["taker"]
            d["feebnbmaker"] = resp["tradeFee"][0]["maker"]
            return d

    def feethreading(self):
        d = dict()
        if "krk" in self.exchange_list:
            krk_fee = Thread(target=lambda q, arg1: q.put(
                self.__fee(arg1)),
                             args=(q1, "krk"))
            krk_fee.start()
        if "trt" in self.exchange_list:
            trt_fee = Thread(target=lambda q, arg1: q.put(
                self.__fee(arg1)),
                             args=(q2, "trt"))
            trt_fee.start()
        if "bnb" in self.exchange_list:
            bnb_fee = Thread(target=lambda q, arg1: q.put(
                self.__fee(arg1)),
                             args=(q3, "bnb"))
            bnb_fee.start()
        try:
            krk_fee.join()

            d.update(q1.get())
        except:
            pass
        try:
            trt_fee.join()

            d.update(q2.get())
        except:
            pass
        try:
            bnb_fee.join()

            d.update(q3.get())
        except Exception:
            pass
        return d

    def tradethreading(self, side, exchange, fund_id, amount, price, side2=None, exchange2=None, fund_id2=None,
                       amount2=None, price2=None):
        d = dict()
        print("bnb")
        bnb_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q1, exchange, fund_id, side, amount, price))
        bnb_trade.start()
        try:
            bnb_trade.join()
        except:
            pass
        try:
            d["bnb"] = q1.get()
        except:
            d["bnb"] = "ERROR"

        return d

    def min_qty_trt(self):
        try:
            resp_trt = requests.get("https://api.therocktrading.com/v1/funds/?id=BTCEUR")
            return json.loads(resp_trt.text)
        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
        except json.decoder.JSONDecodeError:
            print(f"{Fore.RED}[ERR] ERROR WHILE CONVERTING TO JSON [expecting value]{Style.RESET_ALL}")

    def query(self, exchange, pair):
        if exchange == "trt":
            self.trt.pop(1)
            try:
                resp_trt = requests.get('https://api.therocktrading.com/v1/funds/' + self.pair + '/orderbook?limit=1')
                return json.loads(resp_trt.text)
            except requests.exceptions.ConnectionError:
                print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
            except json.decoder.JSONDecodeError:
                print(f"{Fore.RED}[ERR] ERROR WHILE CONVERTING TO JSON [expecting value]{Style.RESET_ALL}")
        elif exchange == "krk":
            resp_krk = requests.get('https://api.kraken.com/0/public/Depth')  # , params=params)
            return resp_krk.text
        elif exchange == "bnb":
            self.bnb.pop(1)
            try:
                resp_bnb = self.client.get_order_book(symbol=self.pair, limit=5)
                return resp_bnb
            except requests.exceptions.ConnectionError:
                print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
            except requests.exceptions.ReadTimeout:
                print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
            except binance.exceptions.BinanceAPIException:
                print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")

    def querythread(self):
        d = dict()
        if "trt" in self.exchange_list:
            self.len = len(self.trt)
            trt_thread = self.trt[1]
            trt_thread.start()

        if "bnb" in self.exchange_list:
            bnb_thread = self.bnb[1]
            bnb_thread.start()

        try:
            trt_thread.join()
            d["trt"] = q1.get()
        except:
            pass
        try:
            bnb_thread.join()
            d["bnb"] = q2.get()
        except:
            pass

        return d
