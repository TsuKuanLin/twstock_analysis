import os
import csv
import time
import twstock
import requests
import glob
from bs4 import BeautifulSoup
from decimal import Decimal, ROUND_HALF_UP

def round_up_to_point_one(input_float): #round up to 0.1
    return str(Decimal(str(input_float)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))

def transform_csv_data(csv_file):
    stock_list = []
    with open(csv_file) as f:
            lines = csv.reader(f,quotechar=',')
            i = 0
            for line in lines:
                i += 1
                if i == 4: # 4th row in csv, find name for each column 
                    try:
                        compCategory = line.index('\"產業\"')
                    except:
                        return ['ERROR:CSV input format wrong!!!']
                if i > 4:
                    cate = line[compCategory].replace('\"','')
                    if cate[1] == "市":
                        stock_list.append('TWSE:'+line[1].replace('\"','').split('.')[0])
                    elif cate[1] == "櫃":
                        stock_list.append('TPEX:'+line[1].replace('\"','').split('.')[0])
                    # print(line[1],line[2],line[11][1],line[11][2:],line[12:])

    return ','.join(stock_list)

def write_output_file(stock_data, endOfLine):

    now = time.localtime()
    time_str = ''.join((str(now.tm_mon).zfill(2), str(now.tm_mday).zfill(2),"選股池XQ"))
    
    if f'{time_str}.txt' in os.listdir('.'):
        time_str = time_str+'_'+str(now.tm_hour)+"_"+str(now.tm_min)
    with open(f'./{time_str}.txt', 'w', encoding="utf-8") as f:
        for lines in stock_data:
            str_ = ' '.join(lines)+endOfLine
            f.write(str_)

def get_stock_list_from_watchlist(url): #爬蟲

    response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')

    comp_list = soup.find(attrs={'name':"description"})['content']

    return comp_list.split(', ')
    
def extract_csv_data(csv_file, stock_list, numTWstock):
    import csv
    stock_data = []
    find = []
    with open(csv_file) as f:
        lines = csv.reader(f,quotechar=',')
        i = 0
        for line in lines:
            i += 1
            if i == 4: # 4th row in csv, find name for each column 
                try:
                    RSRank = line.index('\"排行名次\"')
                    compSymbol = line.index('\"代碼\"')
                    compName = line.index('\"商品\"')
                    compMargin = line.index('\"資券沖期\"')
                    compCategory = line.index('\"產業\"')
                    compDetailedCategory = line.index('細產業')
                except:
                    return ['ERROR:CSV input format wrong!!!']
            if i > 4:
                if line[compSymbol].replace('\"','').split('.')[0] in stock_list:
                    find.append(line[compSymbol].replace('\"','').split('.')[0]) 
                    PR_value = round_up_to_point_one((1 - (int(line[RSRank].replace('\"',''))/numTWstock))* 100 ) 
                    market, mainCate = line[compCategory].replace('\"','')[:2], line[compCategory].replace('\"','')[2:]
                    
                    stock_tmp_data = [int(  line[RSRank].replace('\"','')), 
                                            PR_value, 
                                            line[compSymbol].replace('\"','').split('.')[0],
                                            line[compName].replace('\"',''),
                                            line[compMargin].replace('\"','').split('.')[0],
                                            market, 
                                            mainCate]
                    
                    for category in line[compDetailedCategory:]:
                        stock_tmp_data.append(category)
                    stock_data.append(stock_tmp_data)
    
    stock_data.sort(key= lambda x: x[0])
    not_find = set(stock_list) - set(find) 
    
    data = []
    for line in stock_data:
        data.append(line[1:])            
    return data, not_find

def make_category_hashmap(stock_data):
    map = {}
    times_list = []
    for data in stock_data:
        code, name = data[1], data[2]
        for cate in set(data[4:]):
            if cate not in map :
                if cate != '其他':
                    map[cate] = [''.join((code, name))]
            else:
                map[cate].append(''.join((code, name)))
    
    for cate in map.keys():
        if len(map[cate]) >= 2:
            comp = ' '.join(map[cate])
            times_list.append([str(len(map[cate]))+'次', cate, comp])
    return times_list

def count_numbers_of_twstock(): 
    twstock.__update_codes() 
    num = 0
    for stock in twstock.codes.values():
        if stock[0] == "股票":
            if stock[5] == "上櫃":
                num += 1
            elif stock[5] == "上市":
                num += 1
    return num

def get_nth_largest_csv(folder_path, prefix, day=1):
    # day = 1 為最新的那一個csv檔
    # 取得folder_path裡，以prefix為開頭的csv檔案
    files = glob.glob(os.path.join(folder_path, f"{prefix}*.csv"))
    
    # 如果有檔案，按日期排序
    if files:
        sorted_files = sorted(files, key=lambda x: int(x[-10:-4])) #sort yy/mm/ddd

        # 如果至少有指定的那麼多個檔案，取得第nth大的檔案
        if len(sorted_files) >= day:
            nth_largest_file = sorted_files[-day]
            print(nth_largest_file)
            return nth_largest_file
        else:
            return f"檔案數量不足{day}個"
    else:
        return "資料夾中沒有符合條件的檔案"

if __name__ == "__main__":
    
    print('usage:\t輸入enter:自動將最新的csv轉成股票代碼')
    print('\t只輸入csv檔:將此csv轉成股票代碼')
    print('\t輸入csv檔,股票清單網址:將股票清單中的股票資訊從csv檔中萃取出來')
    user_input = input('請按enter或輸入股票清單:\n')
    user_input = user_input.split(';')
    
    if len(user_input) == 1:

        if not user_input[0]: # directly enter "enter"
            dir = os.path.abspath(get_nth_largest_csv("選股池清單","Mark"))
        else:
            dir = os.path.abspath(user_input[0].replace("\"",""))
        stock_list = transform_csv_data(dir)
        write_output_file(stock_list,'')

    else:
        if "http" in user_input[1]:
            stock_list = get_stock_list_from_watchlist(user_input[1])
        else:
            stock_list = []
            stock_str = user_input[1].split(',')
            for stock in stock_str:
                if ":" in stock:
                    stock_list.append(stock.split(':')[1])
                else:
                    stock_list.append(stock)

        dir = os.path.abspath(user_input[0].replace("\"",""))
        numTWstock = count_numbers_of_twstock()
        stock_data, not_find = extract_csv_data(dir, stock_list, numTWstock)
        
        times_list = make_category_hashmap(stock_data)
        if not times_list:
            times_list = [['無共同細產業']]
        else:
            times_list.sort(key=lambda x: int(x[0].split('次')[0]), reverse=True)
        for stock in not_find:
            stock_data.append([stock,"not find in csv"]) 
        write_output_file(stock_data+times_list,'\n')

        
