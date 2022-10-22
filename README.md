# RFC: 配置兼容性看护

By [seiya-annie](https://github.com/seiya-annie) 

## 概述

配置兼容性看护工具可以对配置变更项进行溯源找到引入变更的 PR；也可以对版本间的配置兼容性进行测试发现兼容性问题。保障版本间的配置变更不会引起兼容性问题。

## 动机

配置参数变更一直是兼容性问题的一个大的引入点。TiDB 产品也非常重视这方面的测试, 目前有两个问题是配置兼容性测试需要改进的：
1. 对于配置变更的跟踪，目前有两条线分别来进行，但彼此信息无法关联起来： 一条跟踪路径是，版本上会要求引起配置变更的每个 pr 进行审批才能合入, 变更信息以 pr 维度来组织。另一条跟踪路径是 QA 会对前后两个版本的实际配置参数进行比较，生成版本间的实际配置变更列表，这个是以配置项为维度进行组织的。QA 拿到实际的变更列表后需要找到引入该变更的 pr 来获取该配置参数的默认值，有效取值范围等来确定测试的预期结果，另外也需要确认该配置项是经过审批的预期变更。但目前无法从 pr 描述上直接找到其实际修改的配置项，需要手工一个个点开去找，效率非常低。
2. 升级后默认值变更和要删除的配置项需要进行测试，保证在新版本上进行了正确的处理，目前这部分是手工测试，需要提供通用的自动化方法： 旧版本升级到新版本需要删除的配置如果不进行忽略处理，会导致升级失败。我们已经发现的升级失败问题，很多是由于这个原因导致的 (https://github.com/pingcap/tidb/issues?q=is%3Aissue+upgrade+fail+author%3Aseiya-annie ）。新旧版本默认值变更的，如果用户指定了该配置值，需要保证升级后与升级前一致。

配置兼容性看护工具预期解决上面两个问题：
1. 提供工具，自动获取实际变更项对应的 PR.
2. 提供测试工具自动对任意两个版本进行配置兼容性测试。
   - 旧版本携带已经在新版本删除的配置项 升级到新版本，升级能够成功。
   - 旧版本携带默认值在新版本已经变更的配置项 升级到新版本，配置项值与升级前一致。

## 项目设计

问题一：获取配置项变更对应的 PR

    step 1: 通过 git blame 命令获取目标配置的变更commit id，例如： 
```code
git blame config.toml.example | grep ddl
0d5ac6f3cb (CbcWestwolf           2022-04-29 13:20:52 +0800 426) # ddl_slow_threshold sets log DDL operations whose execution time exceeds the threshold value.
0d5ac6f3cb (CbcWestwolf           2022-04-29 13:20:52 +0800 427) ddl_slow_threshold = 300
fc217d432c (CbcWestwolf           2022-08-01 15:02:06 +0800 460) # Run ddl worker on this tidb-server.
fc217d432c (CbcWestwolf           2022-08-01 15:02:06 +0800 461) tidb_enable_ddl = true
```
    step 2: 使用 git show 命令，通过 commit id 获取 pr 号
```code
git show fc217d432c
commit fc217d432ce3b8f13cbe94229940db597a1f59fd
Author: CbcWestwolf <1004626265@qq.com>
Date:   Mon Aug 1 15:02:06 2022 +0800

    config, sysvar: add config `instance.enable_ddl` and sysvar `tidb_enable_ddl` (#35425)
    
    ref pingcap/tidb#34960
....
```
    step 3: 生成 config 与 pr 的对应列表


问题二：任意两个版本进行配置兼容性测试

    step 1: 新创建一个 target 版本的 tidb 集群并收集当前配置参数作为对比集，例如v6.4.0。

    step 2: 从 http://tiqa.pingcap.net/dbaas/oncallAnalyse 数据库后台获取 source 版本的默认配置参数

    step 3: 抽取在新版本上有变更或者被删除的配置项列表

    step 4: 生成用户按照 source 版本的 config 文件

    step 5: 使用 step 4 中的配置文件安装 source 版本集群，收集当前配置信息，然后升级到目标版本

    step 6: 收集升级后的配置信息，与升级前的进行比较， 检查实际变更是否与 step 3 中的预期一致。

    step 7: 返回测试结果和测试不通过的配置列表。

