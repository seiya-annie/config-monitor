# This is a sample Python script.
import argparse
import os
import mysqlopt
from fastapi import FastAPI
import git
import re
import tqdm

global COMPONENT, CMDMODULE, FILELIST, VERSION
conn = mysqlopt.mysql_opt()
app = FastAPI()

FILELIST = []

fo = open('pr_check_result', 'a+', encoding='utf-8')
fo.write('-------begin-------\n')


def pull_new_pr(repo):

    print("------begin to pull latest pr ")
    tem_path = '/Users/tingli/git/{}'.format(repo)
    myrepo = git.Repo(path=tem_path)
    mygit = myrepo.git
    res = mygit.checkout('{}'.format("master"))
    print("----------checkout result:", res)
    res = mygit.status()
    print("----------current branch:",res)
    if (str(res).find('{}'.format('error')) != -1):
        exit(2)
    res = mygit.pull()
    print(res)
    if (str(res).find('error') != -1):
        exit(2)

def check_version_valid(version):
    # print("------begin to check_version_valid and get release date by version, version=",version)
    sql_str = "select date_format(release_date, '%Y-%m-%d') from version_lifecycle where version like '%{}%' order by release_date limit 1".format(version)
    res = conn.ExecQuery(sql_str)

    if len(res) == 0:
        print(
            "version is not found, please input correct version. ref https://docs.pingcap.com/zh/tidb/dev/release-notes")
        exit(1)
    return res[0][0]

def check_component_valid(component):
    print("------begin to check_component_valid, component:",component)
    if component == 'tidb':
        COMPONENT = 'tidb'
    elif component == 'tikv':
        COMPONENT = 'tikv'
    elif component == 'pd':
        COMPONENT = 'pd'
    elif component == 'tiflash':
        COMPONENT = 'tiflash'
    elif component == 'sysvar':
        COMPONENT = 'sysvar'
    else:
        "component is incorrect"
        exit(1)
    print("component is :", COMPONENT)

def check_config_list_file_exist():
    print("------begin to check_config_list_file_exist")
    l_repo = ['tidb','tikv','pd','tiflash','sysvar']
    for i in l_repo:
        if os.path.exists("{}_change_list.txt".format(i)):
            FILELIST.append(i)
    print("will check config change list for :",FILELIST)

def get_config_file_by_component(component):
    print("------begin to get_config_file_by_component, component=",component)
    if component == 'tidb':
        configfile = ['/config/config.go']
    elif component == 'tikv':
        configfile = ['/src/config.rs']
    elif component == 'pd':
        configfile = ['/server/config/config.go']
    elif component == 'tiflash':
        configfile = ['/dbms/src/Interpreters/Settings.h']
    elif component == 'sysvar':
        configfile = ['/sessionctx/variable/sysvar.go','/sessionctx/variable/tidb-vars.go']

    print("blame file is :", configfile)
    return configfile

def blame_file_get_commit_id(file,config,repo):
    commit_id_list = []
    print("------begin to blame file, config={0}, repo={1},file={2} ".format(config,repo,file))
    tem_path = '/Users/tingli/git/{}'.format(repo)
    myrepo = git.Repo(path=tem_path)
    # mygit = myrepo.git
    blame = myrepo.blame(None,file)
    print("blame response length:", len(blame))
    min_time = check_version_valid(VERSION)
    print("min_time=", min_time)
    for commit in blame:
        commit_info = commit[1]
        commit_obj = commit[0]
        commit_time = commit_obj.committed_datetime.strftime("%Y-%m-%d")

        if str(commit_info).find(config)!=-1:
            if commit_time < min_time:
                continue
            print("commit id:{0}, commit time: {1}".format(commit,commit_time))
            commit_id_list.append(commit_obj)

    print("commit_id_list is : ",commit_id_list)
    return commit_id_list

def get_commit_id_list_by_config(config):
    print("------begin to get_commit_id_list_by_config, config=",config)
    c_list = []
    if COMPONENT == 'sysvar':
        repo = 'tidb'
    else:
        repo = COMPONENT
    # sync new pr
    pull_new_pr(repo)
    configfile = get_config_file_by_component(COMPONENT)
    tem_path = '/Users/tingli/git/{}'.format(repo)
    for f in configfile:
        print("f=",f)
        fn = tem_path+f
        commit_id = blame_file_get_commit_id(fn,config, repo)
        for id in commit_id:
            c_list.append(id)
        c_list = list(set(c_list))

    print("commit list: ",c_list)
    return c_list

def get_pr_list_by_commit_id(idlist):
    print("begin to get_pr_list_by_commit_id, idlist=",idlist)
    if COMPONENT == 'sysvar':
        repo = 'tidb'
    else: repo = COMPONENT
    pr_list = []
    for id in idlist:
        print("------begin to git show commit id ")
        tem_path = '/Users/tingli/git/{}'.format(repo)
        myrepo = git.Repo(path=tem_path)
        res = myrepo.git.show(id)
        if res == '':
            continue
        if str.find(res,'(#') != -1:
            begin = res.index('(#')
            end = res.index(')')
            pr_no = res[begin+2:end]
            print("pr_no is: ",pr_no)
            pr_list.append(pr_no)
        else:
            print("no pr line:", res)
    return pr_list


def get_pr_list_for_one_config(config):
    if COMPONENT == "tikv" or COMPONENT == "tiflash":
        config = config.replace('-', '_')
    print("begin get_pr_list_for_one_config, config=",config)
    commitID_list = get_commit_id_list_by_config(config.strip())
    pr_list = get_pr_list_by_commit_id(commitID_list)
    print("config changed by pr:", pr_list)
    return pr_list

def get_pr_list_for_config_list():
    print("------begion to get_pr_list_for_config_list")
    for component in FILELIST:
        file_name = "{}_change_list.txt".format(component)
        COMPONENT = component
        print("begin to parse config list in:", file_name)
        fo.write("\n-----result for {} change list-----\n".format(COMPONENT))
        fc = open(file_name, 'r+', encoding='utf-8')

        for line in fc.readlines():
            config_item = line.strip()
            if COMPONENT == "tikv" or COMPONENT == "tiflash":
                config_item.replace('-','_')
            pr_list = get_pr_list_for_one_config(config_item)
            fo.write("{0} : {1}\n".format(config_item,pr_list))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help="config item")
    parser.add_argument('-v', '--version', help="search pr after this version released")
    parser.add_argument('-cp', '--component', help="component config belong to")
    # parser.add_argument('-h', '--help', help="help info")

    args = parser.parse_args()
    if args.config is None:
        # get config item from file
        CMDMODULE = "file"
        check_config_list_file_exist()
        if FILELIST == []:
            print("please add config change list or special the config item by -c")
            exit(1)
    else:
        # get config item from command line
        CMDMODULE = "cml"

    if args.component is None:
        print("please input component to search in")
        exit(1)
    else:
        COMPONENT = args.component
        check_component_valid(args.component)



    # if have a special version to check, and a filter to get pr which merged time is newer than this version released
    if args.version is not None:
        check_version_valid(args.version)
        VERSION = args.version

    if CMDMODULE == 'cml':
        get_pr_list_for_one_config(args.config)

    else:
        get_pr_list_for_config_list()




