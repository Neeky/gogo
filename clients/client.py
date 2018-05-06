#! /usr/bin/env python3
#! -*- encoding: utf8 -*-

import configparser,argparse,requests,bs4,json,logging,sys,os

logging.basicConfig(level = logging.INFO)

def listLogFile(path='./'):
    for filename in os.listdir(path):
        name = os.path.join(path,filename)
        if os.path.isfile(name):
            yield name

def sysbenchLogParser(file_full_path):
    logging.info("start parser {}".format(file_full_path))
    file_name = os.path.basename(file_full_path)
    file_name = file_name.replace('.log','')
    #oltp_update_index#autocommit#0#1
    oltp,variable_name,vairable_value,parallels = file_name.split('#')
    #logging.info("oltp={} variable_name={} vairable_value={} parallels={}".format(oltp,variable_name,vairable_value,parallels))
    with open(file_full_path) as log_file:
        for line in log_file:
            if 'transactions:' in line:
                *_,transactions = line.split('(')
                transactions,*_ = transactions.split('per')
                transactions = int(float(transactions))
            if 'queries:' in line:
                *_,queries = line.split('(')
                queries,*_ = queries.split('per')
                queries = int(float(queries))
    tps = transactions + queries
    #logging.info("tps={}".format(tps))
    result = {'oltp_name':oltp,'parallels':parallels,'scores':tps,
            'variable_name':variable_name,'variable_value':vairable_value}
    logging.info("{}".format(result))
    return result

def opltsAdd(args):
    """
    完成增加oltp测试类型的功能
    """
    #读取配置文件
    logging.info("read config item from {}".format(args.defaults_file))
    config = configparser.ConfigParser()
    config.read(args.defaults_file)

    #求得要提交的olpt类型、提交的目标路径
    oltps = (oltp for oltp in config['default']['oltps'].split(','))
    oplts_len=len(config['default']['oltps'].split(','))
    target_url=config['default']['oltps-add']
    logging.info("target url is {0}".format(target_url))
    for index,oltp in enumerate(oltps):
        logging.info("start add {:<30} to {}".format(oltp,config['default']['host']))
        #打开到target_url的持久连接
        session = requests.Session()
        r = session.get(target_url)
        #解析出csrfmiddlewaretoken的值
        soup = bs4.BeautifulSoup(r.text,'html.parser')
        csrfmiddlewaretoken = soup.find('input',type='hidden')
        token=csrfmiddlewaretoken['value']
        #logging.info("get csrfmiddlewaretoken  {}".format(token))
        r = session.post(target_url,data={'csrfmiddlewaretoken':token,'name':oltp})
        logging.info("compelete {}/{}".format(index,oplts_len))

def environmentsAdd(args):
    """
    完成增加环境信息的功能
    """        
    #读取配置文件
    logging.info("read config item from {}".format(args.defaults_file))
    config = configparser.ConfigParser()
    config.read(args.defaults_file)

    #读取环境信息&提交的目标路径
    target_url=config['default']['environments-add']
    logging.info("read environment info like this {}".format(dict(config['environment'])))

    #准备提交环境信息
    session = requests.Session()
    r = session.get(target_url)
    soup = bs4.BeautifulSoup(r.text,'html.parser')
    csrfmiddlewaretoken = soup.find('input',type='hidden')
    token=csrfmiddlewaretoken['value']
    data=dict(config['environment'])
    if data['is_ssd_disk'] == 'yes':
        data.update({'csrfmiddlewaretoken':token,'is_ssd_disk':True})
    else:
        data.update({'csrfmiddlewaretoken':token,'is_ssd_disk':False})
    r = session.post(target_url,data=data)
    logging.info("post environment info success")

def variablesAdd(args):
    """
    """
    #从参数中解析出mysql版本号
    *_,mysql_version = args.log_path.split('/')
    #读取配置文件中的mysql版本号
    logging.info("read config item from {}".format(args.defaults_file))
    config = configparser.ConfigParser()
    config.read(args.defaults_file)
    target_url=config['default']['variables-add']
    if mysql_version != config['environment']['mysql_release'] :
        logging.warn("log dir diff with config")
        raise SystemExit(1)
    #
    names = (os.path.basename(name) for name in listLogFile(args.log_path) )
    #创建如下类型的集合{ (变量名，变量值) ,(变量名，变量值) }
    variables=set()
    for name in names:
        _,variable_name,variable_value,_ = name.split('#')
        # innodb_buffer_pool_size,2G,_
        variables = variables | {(variable_name,variable_value),}
    for name,value in variables:
        logging.info('start post {}={} to server'.format(name,value))
        session = requests.Session()
        r = session.get(target_url)
        soup = bs4.BeautifulSoup(r.text,'html.parser')
        csrfmiddlewaretoken = soup.find('input',type='hidden')
        token=csrfmiddlewaretoken['value']
        data={'name':name,'value':value,'csrfmiddlewaretoken':token}
        session.post(target_url,data=data)
        logging.info('compelete post {}={} to server'.format(name,value))

def variableScoresAdd(args):
    """
    1、向服务器提交variable_name,variable_value
    """
    #什么都不管上来就向服务器提交variable_name,variable_value的对应信息
    variablesAdd(args)
    #解析出environment_name,target_url,variablescores-add,mysql_release
    logging.info("read config item from {}".format(args.defaults_file))
    config = configparser.ConfigParser()
    config.read(args.defaults_file)
    #开始读取配置
    target_url=config['default']['variablescores-add']
    environment_name = config['environment']['name']
    mysql_release    = config['environment']['mysql_release']
    for log_file in listLogFile(args.log_path):
        data = sysbenchLogParser(log_file)
        data.update({'environment_name':environment_name,'mysql_release':mysql_release})
        logging.info("all datas like this {}".format(data))
        session = requests.Session()
        r = session.get(target_url)
        soup = bs4.BeautifulSoup(r.text,'html.parser')
        csrfmiddlewaretoken = soup.find('input',type='hidden')
        token=csrfmiddlewaretoken['value']
        data.update({'csrfmiddlewaretoken':token})
        session.post(target_url,data=data) 

def tuningScoresAdd(args):
    """
    """
    logging.info("start tuningSocresAdd function ")
    config = configparser.ConfigParser()
    config.read(args.defaults_file)  
    target_url=config['default']['tunings-add']
    logging.info("use environment.name as name")
    logging.info("target url is {}".format(target_url))
    name = config['environment']['name']
    data={'name':name}
    for log_file in listLogFile(args.log_path):
        raw_data = sysbenchLogParser(log_file)
        data.update({'step':raw_data['variable_value'],
                    'parallels':raw_data['parallels'],
                    'scores':raw_data['scores']})
        session = requests.Session()
        r = session.get(target_url)
        soup = bs4.BeautifulSoup(r.text,'html.parser')
        csrfmiddlewaretoken = soup.find('input',type='hidden')
        logging.info("{}".format(csrfmiddlewaretoken))
        token=csrfmiddlewaretoken['value']
        data.update({'csrfmiddlewaretoken':token})
        r=session.post(target_url,data=data)
        soup = bs4.BeautifulSoup(r.text,'html.parser')
        logging.info(soup.title)




argsToFun={
    'oltps-add': opltsAdd,
    'environments-add': environmentsAdd,
    #'variables-add': variablesAdd,
    'variablescores-add': variableScoresAdd,
    'tuningscores-add':tuningScoresAdd,
}    

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--defaults-file',default='sqlpy.cnf',help='默认配置文件./sqlpy.cnf')
    parser.add_argument('--log-path',default='/Users/jianglexing/Desktop/mysql-5.7.22',help='sysbench 日志文件所保存的路径')
    parser.add_argument('action',choices=('oltps-add','environments-add','variablescores-add','tuningscores-add'))
    args=parser.parse_args()
    argsToFun[args.action](args)


