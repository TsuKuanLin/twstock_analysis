import os
import csv
import time
import glob
import requests
from bs4 import BeautifulSoup
from decimal import Decimal, ROUND_HALF_UP

colors = ['#F3C300', '#875692', '#F38400', '#A1CAF1', '#BE0032', '#C2B280', '#848482', '#008856', '#E68FAC', '#0067A5', '#F99379', '#604E97', '#F6A600', '#B3446C', '#DCD300', '#882D17', '#8DB600', '#654522', '#E25822', '#2B3D26']

def round_up_to_point_one(input_float): #round up to 0.1
    return str(Decimal(str(input_float)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))

def transform_csv_data(csv_file):
    stock_list = []
    with open(csv_file) as f:
            lines = csv.reader(f,quotechar=',')
            i = 0
            for line in lines:
                i += 1
                if i == 4: # 4th row in csv, find name for each column, 當XQ output header有改變要改這行
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

def write_output_file(stock_data, endOfLine, filename):

    now = time.localtime()
    if filename == "XQ":
        time_str = ''.join((str(now.tm_mon).zfill(2), str(now.tm_mday).zfill(2),filename)) 
    else:
        time_str = ''.join((str(now.tm_mon).zfill(2), str(now.tm_mday).zfill(2),filename)) + "_1"
    
    if glob.glob(os.path.join(f'{time_str[:-2]}*.txt')):
        time_str = os.path.basename(glob.glob(os.path.join(f'{time_str[:-2]}*.txt'))[-1])
        time_str = '_'.join([*time_str.split('_')[:-1],str(int(time_str.split('_')[-1].split('.')[0])+1)])

    with open(f'./{time_str}.txt', 'w', encoding="utf-8") as f:
        for lines in stock_data:
            str_ = ' '.join(lines)+endOfLine
            f.write(str_)

def get_stock_list_from_watchlist(url): #爬蟲, get stock info from tradingview.com

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    comp_list = soup.find(attrs={'name':"description"})['content']

    return comp_list.split(', ')
    
def find_numTWstock_by_same_date(Mark_path): # find "All_date.csv" by "Mark_date.csv"

    date, base_dir = os.path.basename(Mark_path)[-12:-4], os.path.dirname(Mark_path)
    all_stock_csv_path = glob.glob(os.path.join(base_dir,f'All*{date}.csv'))[0]

    with open(all_stock_csv_path) as f:
        numTWstock = sum(1 for row in csv.reader(f,quotechar=',')) - 4 # total row minus header, if XQ header has change, then revise this

    return numTWstock, date

def extract_csv_data(csv_file, stock_list):
    
    stock_data, find = [], []
    numTWstock, _ = find_numTWstock_by_same_date(csv_file)
    with open(csv_file) as f:
        lines = csv.reader(f,quotechar=',')
        i = 0
        for line in lines:
            i += 1
            if i == 4: # 4th row in csv, find name for each column 
                try:
                    RSRank_index = line.index('\"排行名次\"')
                    compSymbol_index = line.index('\"代碼\"')
                    compName_index = line.index('\"商品\"')
                    compMargin_index = line.index('\"資券沖期\"')
                    compCategory_index = line.index('\"產業\"')
                    compDetailedCategory_index = line.index('細產業')
                except:
                    return ['ERROR:CSV input format wrong!!!']
            if i > 4:
                if line[compSymbol_index].replace('\"','').split('.')[0] in stock_list:
                    find.append(line[compSymbol_index].replace('\"','').split('.')[0]) 
                    PR_value = round_up_to_point_one((1 - (int(line[RSRank_index].replace('\"',''))/numTWstock))* 100 ) 
                    market, mainCate = line[compCategory_index].replace('\"','')[:2], line[compCategory_index].replace('\"','')[2:]
                    
                    stock_tmp_data = [int(  line[RSRank_index].replace('\"','')), 
                                            PR_value, 
                                            line[compSymbol_index].replace('\"','').split('.')[0],
                                            line[compName_index].replace('\"',''),
                                            line[compMargin_index].replace('\"','').split('.')[0],
                                            market, 
                                            mainCate]
                    
                    for category in line[compDetailedCategory_index:]:
                        stock_tmp_data.append(category)
                    stock_data.append(stock_tmp_data)
    
    stock_data.sort(key= lambda x: x[0])
    not_find = set(stock_list) - set(find) 
    
    data = []
    for line in stock_data:
        data.append(line[1:])            
    return data, not_find

def make_category_hashmap(stock_data): #count 共同細項
    map = {}
    times_list = []
    for data in stock_data:
        code, name = data[1], data[2]
        for cate in set(data[5:]):
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

def get_nth_largest_csv(folder_path, prefix, day=1):
    # day = 1 為最新的那一個csv檔
    # 取得folder_path裡，以prefix為開頭的csv檔案
    files = glob.glob(os.path.join(folder_path, f"{prefix}*.csv"))
    
    # 如果有檔案，按日期排序
    if files:
        sorted_files = sorted(files, key=lambda x: int(x[-10:-4])) #sort yy/mm/ddd

        # 如果至少有指定的多個檔案，取得第nth大的檔案
        if len(sorted_files) >= day:
            nth_largest_file = sorted_files[-day]
            print(nth_largest_file)
            return nth_largest_file
        else:
            return f"檔案數量不足{day}個"
    else:
        return "資料夾中沒有符合條件的檔案"
    
def extract_RS_ranking_from_csv(csv_file, stock_list): # only extract comp Name, RS ranking from All_date.csv
    
    numTWstock, date = find_numTWstock_by_same_date(csv_file)

    with open(csv_file) as f:
        lines = csv.reader(f,quotechar=',')
        i = 0
        find, data_dict, compName_dict = [], dict(), dict()
        for line in lines:
            i += 1
            if i == 4: # 4th row in csv, find name for each column 
                try:
                    RSRank = line.index('\"排行名次\"')
                    compSymbol_index = line.index('\"代碼\"')
                    compName_index = line.index('\"商品\"') 
                except:
                    return ['ERROR:CSV input format wrong!!!']
            if i > 4:
                if line[compSymbol_index].replace('\"','').split('.')[0] in stock_list:
                    find.append(line[compSymbol_index].replace('\"','').split('.')[0]) 
                    PR_value = round_up_to_point_one((1 - (int(line[RSRank].replace('\"',''))/numTWstock))* 100 )
                    data_dict[line[compSymbol_index].replace('\"','').split('.')[0]] = float(PR_value)
                    compName_dict[line[compSymbol_index].replace('\"','').split('.')[0]] = line[compName_index].replace('\"','')
        not_find = set(stock_list) - set(find)
        
        for stock in not_find:
            data_dict[stock] = None

        data = [data_dict[stock] for stock in stock_list]
    return data, date, compName_dict

def draw_historical_RS_ranking_plot(start, end, stock_list):

    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.pyplot import MultipleLocator

    matplotlib.rc('font', family='MingLiU') # 新細明體，微軟正黑體有超大行距

    figSize = len(stock_list)
    if figSize <= 10:
        ratio = 1
    else:
        ratio = 1+(figSize-10)/10*2

    plt.figure(figsize=(8*ratio, 6*ratio)) # 800x600 dpi
    ax = plt.axes()
    ax.yaxis.set_major_locator(MultipleLocator(1))

    dates, RS_ranking_data, legend =  [], [], []
    for nth in range(end, start-1, -1):
        data, date, compName_dict = extract_RS_ranking_from_csv(get_nth_largest_csv("選股池清單","All",day=nth), stock_list)
        dates.append(date[4:6]+"/"+date[6:])
        RS_ranking_data.append(data)
    
    for idx in range(len(stock_list)): 
        if idx < 20:
            plt.plot(dates, [RS_ranking_data[i][idx] for i in range(end-start+1)], '-o', color=colors[idx], zorder=len(stock_list)-idx)
        else:
            plt.plot(dates, [RS_ranking_data[i][idx] for i in range(end-start+1)], '-o', zorder=len(stock_list)-idx)
        legend.append(stock_list[idx]+compName_dict[stock_list[idx]])

    now = time.localtime()
    time_str = ''.join((str(now.tm_mon).zfill(2), str(now.tm_mday).zfill(2)+"_RS_1"))

    if glob.glob(os.path.join(f'{time_str[:-2]}*.png')):
        time_str = os.path.basename(glob.glob(os.path.join(f'{time_str[:-2]}*.png'))[-1])
        time_str = '_'.join([*time_str.split('_')[:-1],str(int(time_str.split('_')[-1].split('.')[0])+1)])
    
    plt.subplots_adjust(right=0.7)
    plt.title(time_str)
    plt.xlabel('日期')
    plt.ylabel('RS ranking')
    plt.legend(legend, loc='center left', bbox_to_anchor=(1.04, 0.5))
    plt.savefig(time_str+".png")

if __name__ == "__main__":
    
    def usage():
        print('usage:\t輸入enter:\t自動將最新的csv轉成股票代碼')
        print('\t股票清單網址: 將股票清單中的股票資訊從最新的csv檔中萃取出來，依照股票清單的股票擷取20天的RS ranking資料並畫圖')
        print('\t股票清單網址;日期: 萃取當日資料後，依照股票清單的股票擷取輸入日期的RS ranking資料並畫圖')
        print('\t日期格式:\t只輸入單一數字(N):擷取第一天(當天)到第N天前的資訊')
        print('\t\t\t輸入A-B(B>A):擷取第A天前到第B天前的資訊')

    usage()
    user_input = input('請按enter或輸入股票清單:\n')
    user_input = user_input.split(';')
    
    if ".csv" in user_input[0]:
        dir = os.path.abspath(user_input[0].replace("\"",""))

        if len(user_input) == 1:
            stock_list = transform_csv_data(dir)
            write_output_file(stock_list,'',"XQ")

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
        stock_data, not_find = extract_csv_data(dir, stock_list)
        times_list = make_category_hashmap(stock_data)
        if not times_list:
            times_list = [['無共同細產業']]
        else:
            times_list.sort(key=lambda x: int(x[0].split('次')[0]), reverse=True)
        for stock in not_find:
            stock_data.append([stock,"not find in csv"]) 
        write_output_file(stock_data+times_list,'\n', "sector")

    else:
        dir = os.path.abspath(get_nth_largest_csv("選股池清單","Mark"))

        if not user_input[0]:    
            stock_list = transform_csv_data(dir)
            write_output_file(stock_list,'',"XQ")

        else:
            if "http" in user_input[0]:
                stock_list = get_stock_list_from_watchlist(user_input[0])
            else:
                stock_list = []
                stock_str = user_input[0].split(',')
                for stock in stock_str:
                    if ":" in stock:
                        stock_list.append(stock.split(':')[1])
                    else:
                        stock_list.append(stock)

            stock_data, not_find = extract_csv_data(dir, stock_list)

            # 將原本的 RS 後面連接 Fundamental RS
            dir_fund = os.path.abspath(get_nth_largest_csv("選股池清單","Fund"))
            stock_data_fund, not_find_fund = extract_csv_data(dir_fund, stock_list)
            stock_data_fund_dict = dict()

            for stock_fund in stock_data_fund:
                stock_data_fund_dict[stock_fund[1]] = stock_fund[0]
            
            for stock in stock_data:
                stock[0] = ','.join([stock[0],stock_data_fund_dict[stock[1]]])  

            # find history RS ranking
            
            if len(user_input) == 2:
                #deal with input, defaulth start=1
                dates = user_input[1].split('-')
                if len(dates) == 1:
                    start, end = 1, int(dates[0])
                else:
                    start, end = int(dates[0]), int(dates[1]) 
            else:
                #default start=1
                start, end = 1, 20
            draw_historical_RS_ranking_plot(start, end, stock_list)

            times_list = make_category_hashmap(stock_data)
            if not times_list:
                times_list = [['無共同細產業']]
            else:
                times_list.sort(key=lambda x: int(x[0].split('次')[0]), reverse=True)
            for stock in not_find:
                stock_data.append([stock,"not find in csv"]) 
            write_output_file(stock_data+times_list,'\n',"sector")
    print("程式跑完了...")
    time.sleep(1)