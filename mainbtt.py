import datetime
import decimal
import json
import time
import requests
from kucoin.client import Market
from kucoin.client import Trade
from kucoin.client import User


def main():
    d = dict()
    with open("keydict.txt", "r") as f:
        key, secret, password = f.read().split(",")
    client_m = Market(url='https://api.kucoin.com')
    client_t = Trade(key=key, secret=secret, passphrase=password, is_sandbox=False, url='')
    client_u = User(key, secret, password)
    while True:
        #try:
            order_id_sell = ""
            while order_id_sell == "":
                a = str(client_u.get_account_list(currency="WIN", account_type="trade")[0]).replace("'", r'"')
                print(a)
                bal_bax = json.loads(a)["balance"]
                print("ALT BALANCE: ", bal_bax)
                price_list = \
                    json.loads(str(client_m.get_aggregated_order(symbol="WIN-BTC")).replace("'", r'"'))["asks"][0]
                print("SELL PRICE, SELL DEPTH: ", price_list)
                bax_bid_price, bax_bid_depth = price_list[0], price_list[1]
                print("PREZZO DA UTILIZZARE PER SELLARE", float_to_str(float(bax_bid_price) * 1.00)[:12])
                try:
                    buy = 10000.0
                    price = float_to_str(float(bax_bid_price) * 1.00)
                    order_id_sell = client_t.create_limit_order('WIN-BTC', 'sell', str(buy), price[:12])["orderId"]
                except Exception as err:
                    print("ERRORE NEL PIAZZARE SELL, REINIZIO DACCAPO", str(datetime.datetime.utcnow()) + str(err))
                    with open("log.txt", "a") as f:
                        f.write("ERRORE NEL PIAZZARE SELL, REINIZIO DACCAPO " + str(datetime.datetime.utcnow()) + str(
                            err) + "\n")
                        f.close()
                    continue
                time.sleep(5)
                print("ORDINE SELL PIAZZATO", order_id_sell)
                print("DETTAGLI ORDINE SELL", json.loads(
                    str(client_t.get_order_details(orderId=str(order_id_sell)))
                        .replace("'", r'"')
                        .replace("False", '"False"')
                        .replace("True", '"True"')
                        .replace("None", '"None"'))["isActive"])
                creato = int(time.time())
                with open("log.txt", "a") as f:
                    f.write("SELL PIAZZATO " + str(datetime.datetime.utcnow()) + "\n")
                    f.close()
            #           SELL PIAZZATO, PROCEDO A VERIFICARE SE IL SELL E' ANCORA APERTO
            ordine_in_corso = True
            while ordine_in_corso:
                try:
                    if not json.loads(
                        str(client_t.get_order_details(orderId=str(order_id_sell)))
                                .replace("'", r'"')
                                .replace("False", '"False"')
                                .replace("True", '"True"')
                                .replace("None", '"None"'))["isActive"] == "True":
                        ordine_in_corso=False
                except Exception as err:
                    print("ERRORE CONNESSIONE CON KUCOIN",err)
                    with open("log.txt","w") as f:
                        f.write("ERRORE CONNESSIONE CON KUCOIN "+str(datetime.datetime.utcnow())+str(err)+"\n")
                        f.close()
                    continue
                if int(time.time()) - creato > 120:
                    try:
                        a = str(client_u.get_account_list(currency="WIN", account_type="trade")[0]).replace("'", r'"')
                        client_t.cancel_order(orderId=order_id_sell)
                        bal_bax = json.loads(a)["balance"]
                        print("BALANCE: ", bal_bax)
                        buy = 10000.0
                        price_list = json.loads(str(client_m.get_aggregated_order(symbol="WIN-BTC"))
                                                .replace("'", r'"'))["asks"][0]
                        bax_bid_price, bax_bid_depth = price_list[0], price_list[1]
                        price = float_to_str(float(bax_bid_price) * 1.00)
                        order_id_sell = client_t.create_limit_order('WIN-BTC', 'sell', str(buy), price[:12])["orderId"]
                        creato = int(time.time())
                        time.sleep(5)
                    except Exception:
                        pass
                print("ATTENDO IL SELL")
                with open("log.txt", "a") as f:
                    f.write("ATTENDO IL SELL" + "\n")
                    f.close()
                print(json.loads(str(client_t.get_order_details(orderId=str(order_id_sell)))
                                 .replace("'", r'"')
                                 .replace("False", '"False"')
                                 .replace("True", '"True"')
                                 .replace("None", '"None"'))["isActive"])
                time.sleep(10)
            #           ORDINE SELL FILLATO O CANCELLATO, PROCEDO A METTERE BUY

            a = str(client_u.get_account_list(currency="BTC", account_type="trade")[0]).replace("'", r'"')
            print("INFO CONTO BTC", a)
            with open("log.txt", "a") as f:
                f.write("INFO CONTO BTC" + a + "\n")
                f.close()
            bal_btc = json.loads(a)["available"]
            print("BTC BALANCE: ", bal_btc)
            with open("log.txt", "a") as f:
                f.write("BALANCE BTC" + bal_btc + "\n")
                f.close()
            price_list = json.loads(str(client_m.get_aggregated_order(symbol="WIN-BTC")).replace("'", r'"'))["asks"][0]
            print("price, depth: ", price_list)
            depth = 10000.0
            price = float_to_str(float(price) - 0.0000000001)
            print("ordine", price[:12])
            order_id_buy = client_t.create_limit_order('WIN-BTC', 'buy', "10000", price[:12])["orderId"]
            with open("log.txt", "a") as f:
                f.write("ORDINE BUY CREATO" + order_id_buy + "\n")
                f.close()
            time.sleep(6)
            try:
                if json.loads(str(client_t.get_order_details(orderId=str(order_id_buy)))
                                      .replace("'", r'"')
                                      .replace("False", '"False"')
                                      .replace("True", '"True"')
                                      .replace("None", '"None"'))["isActive"] == "True":
                    print("ok, ordine buy creato")
                    time.sleep(5)
            except Exception as err:
                with open("log.txt", "a") as f:
                    f.write("ERRORE CREAZIONE ORDINE BUY " + str(datetime.datetime.utcnow()) + str(err) + "\n")
                    f.close()
                order_id_buy = client_t.create_limit_order('WIN-BTC', 'buy', depth, price[:12])["orderId"]
            creato = int(time.time())
            while json.loads(str(client_t.get_order_details(orderId=str(order_id_buy)))
                                     .replace("'", r'"')
                                     .replace("False", '"False"')
                                     .replace("True", '"True"')
                                     .replace("None", '"None"'))["isActive"] == "True":
                print("Attendo")
                print(json.loads(str(client_t.get_order_details(orderId=str(order_id_buy)))
                                 .replace("'", r'"')
                                 .replace("False", '"False"')
                                 .replace("True", '"True"')
                                 .replace("None", '"None"'))["isActive"])
                time.sleep(2)
                print(int(time.time()) - creato)
                if int(time.time()) - creato > 30:
                    break
        #except Exception as err:
        #    with open("log.txt", "a") as f:
        #        f.write("ERRORE GENERALE " + str(err) + "\n")
        #        f.close()
        #    pass


ctx = decimal.Context()

# 20 digits should be enough for everyone :D
ctx.prec = 20


def float_to_str(f):
    """
    Convert the given float to a string,
    without resorting to scientific notation
    """
    d1 = ctx.create_decimal(repr(f))
    return format(d1, 'f')


if __name__ == '__main__':
    main()
