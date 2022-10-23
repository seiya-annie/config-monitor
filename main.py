# This is a sample Python script.
import argparse
import os
import mysqlopt
import git
import re

global COMPONENT, CMDMODULE, FILELIST, VERSION, CHANGEMODE
conn = mysqlopt.mysql_opt()
topo = open("topo.yaml", 'w+', encoding='utf-8')
FILELIST = []


def pull_new_pr():
    repos = ['tidb','tikv','pd','tiflash']
    for i in repos:
        print("------begin to pull latest pr ")
        tem_path = '/Users/tingli/git/{}'.format(i)
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
        configfile = ['/src/config.rs','/components/raftstore/src/store/config.rs',
                      '/components/causal_ts/src/config.rs']
    elif component == 'pd':
        configfile = ['/server/config/config.go']
    elif component == 'tiflash':
        configfile = ['/dbms/src/Interpreters/Settings.h']
    elif component == 'sysvar':
        configfile = ['/sessionctx/variable/sysvar.go','/sessionctx/variable/tidb_vars.go']

    print("blame file is :", configfile)
    return configfile

def blame_file_get_commit_id(file,config,repo):
    commit_id_list = []
    print("------begin to blame file, config={0}, repo={1},file={2} ".format(config,repo,file))
    tem_path = '/Users/tingli/git/{}'.format(repo)
    myrepo = git.Repo(path=tem_path)
    # mygit = myrepo.git
    blame = myrepo.blame(None,file)
    # print("blame response length:", len(blame))
    min_time = check_version_valid(VERSION)
    print("min_time=", min_time)
    for commit in blame:
        commit_info = commit[1]
        commit_obj = commit[0]
        commit_time = commit_obj.committed_datetime.strftime("%Y-%m-%d")

        if str(commit_info).find(config)!=-1:
            if commit_time < min_time:
                continue
            # print("commit id:{0}, commit time: {1}".format(commit,commit_time))
            commit_id_list.append(commit_obj)

    # print("commit_id_list is : ",commit_id_list)
    return commit_id_list

def get_commit_id_list_by_config(config):
    print("------begin to get_commit_id_list_by_config, config=",config)
    c_list = []
    if COMPONENT == 'sysvar':
        repo = 'tidb'
    else:
        repo = COMPONENT
    configfile = get_config_file_by_component(COMPONENT)
    tem_path = '/Users/tingli/git/{}'.format(repo)
    for f in configfile:
        # print("f=",f)
        fn = tem_path+f
        commit_id = blame_file_get_commit_id(fn,config, repo)
        for id in commit_id:
            c_list.append(id)
        c_list = list(set(c_list))

    print("commit list: ",c_list)
    return c_list

def get_pr_list_by_commit_id(idlist):
    # print("begin to get_pr_list_by_commit_id, idlist=",idlist)
    if COMPONENT == 'sysvar':
        repo = 'tidb'
    else: repo = COMPONENT
    pr_list = []
    for id in idlist:
        tem_path = '/Users/tingli/git/{}'.format(repo)
        myrepo = git.Repo(path=tem_path)
        res = myrepo.git.show(id)
        if res == '':
            continue
        if str.find(res,'(#') != -1:
            begin = res.index('(#')
            end = res.index(')')
            pr_no = res[begin+2:end]
            # print("pr_no is: ",pr_no)
            pr_list.append(pr_no)
        else:
            print("no pr line:", res)
    return pr_list

def change_id_link(pr_list):
    pre_str = ""
    link_list = []
    if COMPONENT == "tikv":
        pre_str = "https://github.com/tikv/tikv/pull/"
    elif COMPONENT == "tidb" or COMPONENT == "sysvar":
        pre_str = "https://github.com/pingcap/tidb/pull/"
    elif COMPONENT == "pd":
        pre_str = "https://github.com/tikv/pd/"
    elif COMPONENT == "tiflash":
        pre_str = "https://github.com/pingcap/tidb/pull/"
    for pr in pr_list:
        link_list.append(pre_str + pr)
    return link_list

def get_pr_list_for_one_config(config):
    if COMPONENT == "tikv" or COMPONENT == "tiflash":
        config = config.replace('-', '_')
    if CHANGEMODE == 'update':
        chars = re.split('-|_',config)
        new = ''
        for i in chars:
            new.join(i.capitalize())
        config = new
    print("begin get_pr_list_for_one_config, config=",config)
    commitID_list = get_commit_id_list_by_config(config.strip())
    pr_list = get_pr_list_by_commit_id(commitID_list)
    pr_link_list = change_id_link(pr_list)
    print("config changed by pr:", pr_link_list)
    return pr_link_list

def get_pr_list_for_config_list():
    global CHANGEMODE, COMPONENT
    print("------begion to get_pr_list_for_config_list")

    foo = open('pr_check_result', 'w+', encoding='utf-8')
    foo.write('-------begin-------\n')

    for component in ['tidb','tikv','pd','tiflash','sysvar']:
        file_name = "{}_change_list.txt".format(component)
        COMPONENT = component
        print("begin to parse config list in:", file_name)
        foo.write("\n-----result for {} change list-----\n".format(COMPONENT))
        fc = open(file_name, 'r+', encoding='utf-8')

        for line in fc.readlines():
            param = str(line).split(',')
            if line == '' or param == []:
                continue
            config_item = param[0].split('=')[0].strip()
            last_config = config_item.split('.')[-1]
            if COMPONENT == "tikv" or COMPONENT == "tiflash":
                last_config = last_config.replace('-','_')

            CHANGEMODE = param[1].strip()
            print("config_item:%s,change_mode:%s", config_item,CHANGEMODE)
            pr_list = get_pr_list_for_one_config(last_config)
            foo.write("{0} : {1}\n".format(config_item,pr_list))
    foo.close()

def get_new_added_list(repo,oldversion,newversion,file):
    sql_str = "SELECT  *, 'add' FROM \
                 ( SELECT \
                    b.item_name, \
                    a.default_value AS 'version1', \
                    b.default_value AS 'version2', \
                    b.value_type AS 'type' \
                   FROM  ( \
                    SELECT *  FROM tbl_{2} WHERE version = '{0}') a \
                   RIGHT JOIN (\
                    SELECT  item_name, default_value,value_type FROM tbl_{2} WHERE  version = '{1}' \
                 ) b ON a.item_name = b.item_name ) c where c.version1 is null;".format(oldversion, newversion, repo)
    res = conn.ExecQuery(sql_str)
    # print(res)

    if len(res) == 0:
        return

    for i in res:
        if (str(i[0]).startswith("raftstore-proxy") or str(i[0]).startswith("engine-store.flash.tidb_status_addr")) and repo == 'tiflash':
            continue
        if str(i[0]).startswith("schedule.store-limit") and repo == 'pd':
            continue
        if i[3] == 'str':
            value = "'" + str(i[2]).replace('\n','') + "'"
        else: value = str(i[2]).replace('\n','')
        item = i[0] + '=' + value + ',' + i[-1]
        file.write(item)
        file.write("\n")

def get_deleted_list(repo,oldversion,newversion,file):
    sql_str = "SELECT  *, 'delete' FROM \
                 ( SELECT \
                    a.item_name, \
                    a.default_value AS 'version1', \
                    b.default_value AS 'version2', \
                    a.value_type AS 'type' \
                   FROM  ( \
                    SELECT  item_name, default_value, value_type FROM tbl_{2} WHERE version = '{0}') a \
                   LEFT JOIN (\
                    SELECT  * FROM tbl_{2} WHERE  version = '{1}' \
                 ) b ON a.item_name = b.item_name ) c where c.version2 is null;".format(oldversion,newversion,repo)
    res = conn.ExecQuery(sql_str)
    # print(res)

    if len(res) == 0:
        return

    for i in res:
        if str(i[0]).startswith("raftstore-proxy") and repo=='tiflash':
            continue
        if i[3] == 'str':
            value = "'" + str(i[1]).replace('\n','') + "'"
        else: value = str(i[1]).replace('\n','')
        item = i[0] + '=' + value + ',' + i[-1]
        file.write(item)
        file.write("\n")
        topo.write(i[0] + ': ' + value + "\n")

def get_update_list(repo,oldversion,newversion,file):
    sql_str = "SELECT  *, 'update' FROM \
                     ( SELECT \
                        a.item_name, \
                        a.default_value AS 'version1', \
                        b.default_value AS 'version2', \
                        a.value_type AS 'type' \
                       FROM  ( \
                        SELECT  * FROM tbl_{2} WHERE version = '{0}') a \
                        JOIN (\
                        SELECT  item_name, default_value,value_type  FROM tbl_{2} WHERE  version = '{1}' \
                     ) b ON a.item_name = b.item_name ) c where c.version2<>c.version1;".format(oldversion, newversion,
                                                                                            repo)
    res = conn.ExecQuery(sql_str)
    # print(res)

    if len(res) == 0:
        return

    for i in res:
        if str(i[0]).startswith("raftstore-proxy") and repo=='tiflash':
            continue
        if i[3] == '\'str\'':
            value = "'" + str(i[1]).replace('\n','') + "'"
        else: value = str(i[1]).replace('\n','')

        item = i[0] + '=' + value + ',' + i[-1]
        file.write(item)
        file.write("\n")
        topo.write(i[0] + '=' + value + "\n")

def get_config_diff(old,new):
    l_repo = ['tidb', 'tikv', 'pd', 'tiflash', 'sysvar']

    for i in l_repo:
        file_name = "{}_change_list.txt".format(i)
        # print("begin to create:", file_name)
        topo.write(i+":\n")
        fo = open(file_name, 'w+', encoding='utf-8')
        get_new_added_list(i,old, new,fo)
        get_deleted_list(i,old,new,fo)
        get_update_list(i,old,new,fo)
        fo.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--checkmode', help="cmd/file")
    parser.add_argument('-c', '--config', help="config item")
    parser.add_argument('-v', '--version', help="search pr after this version released")
    parser.add_argument('-cp', '--component', help="component config belong to")
    parser.add_argument('-cm', '--changemode', help="add/update/delete")
    parser.add_argument('-ov', '--oldversion', help="old version for diff config")
    parser.add_argument('-nv', '--newversion', help="new version for diff config")
    # parser.add_argument('-h', '--help', help="help info")

    args = parser.parse_args()
    if args.checkmode == 'cmd':
        CMDMODULE = "cmd"
        if args.config is None:
            print("please special the config item by -c")
            exit(1)
        if args.component is None:
            print("please input component to search in")
            exit(1)
        else:
            COMPONENT = args.component
            check_component_valid(args.component)
        if args.changemode is None:
            CHANGEMODE = 'add'
        else: CHANGEMODE = args.changemode
    elif args.checkmode == 'file':
        CMDMODULE = "file"
        if args.oldversion is None:
            print("please input old version by -ov")
            exit(1)
        if args.newversion is None:
            print("please input new version by -ov")
            exit(1)

    # if have a special version to check, and a filter to get pr which merged time is newer than this version released
    if args.version is not None:
        check_version_valid(args.version)
        VERSION = args.version
    else: VERSION = args.oldversion
    # sync new pr
    pull_new_pr()
    print("begin to diff cofig for {0} and {1}".format(args.oldversion,args.newversion))
    get_config_diff(args.oldversion,args.newversion)
    check_config_list_file_exist()

    if CMDMODULE == 'cmd':
        get_pr_list_for_one_config(args.config)
    else:
        get_pr_list_for_config_list()


    conn.Close()
    topo.close()




