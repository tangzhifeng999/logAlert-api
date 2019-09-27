###项目介绍
    logAlert项目的设计主要目的能够监控项目日志文件，针对项目日志文件中出现的需要关注的日志类型，进行项目告警和统计工作。
    对于满足告警条件的告警信息进行相关记录，然后项目相关的负责人可以针对处理解决。
###背景
    基于ELK----日志分析平台，ELK上面搭建好了项目日志，该项目基于elk的查询规则，监控相关规则数据。可以避免项目的相关责任
    人需要定期定时的登录查看，避免错误信息发现不及时，造成较大的影响。
###数据库结构
    用户(adminUser)
        _id: ObjectId   
        name: (str)  成员真实姓名
        mobile: (str)  成员手机号
        email: (str)  成员邮箱
        password: (str)  密码
        status: (bool)  状态：启用和禁用
---
    项目表（project）
        _id:ObjectId
        app:(str)   项目代号，需要和elk系统中配置的查询参数项目代号相匹配
        name:(str)  项目中文名称，可以随意指定，一般是我们平时项目口头名称即可
        tasks_num:(int)   轮询任务数，需要定时间隔几分钟的监控任务数量
        count_tasks_num:(int)   统计任务数，不需要输出到日志告警系统，只是发送邮箱通知相关责任人
---
    告警信息表(logInfo)
        _id:ObjectId
        app:(str) 项目代号
        name:(str) 项目名称
        type:(str)  日志类型：目前elk配置的日志类型主要有两种apilog和nginx-access
        path:(str)   日志文件的路径
        level:(str)   日志文件的参数，如果是apilog对应的参数为错误等级，如果是nginx-access，参数为状态码
        status:(int)
            0：(int)待处理
            1：(int)处理中
            2：(int)已完成
            3：(int)不再告警   项目相关负责人可以直接关闭告警，备注信息必填，开发人员认为不存在安全隐患，可以设置为不再告警。
        loginfo:(dict) 
            md5:(str) ：这个字段只是为了方便数据存储，意识mongo不能存储存在.的键，其次键不能太长。
            message:(str)：apilog对应的就是message。nginx-access对应的就是uri.
            timeline:(list):指的是在elk中出现该查询规则的时间。
        update_time:(str)：数据库记录这个告警信息日期
        time: 数据库记录这个告警信息的时间
 ---
    处理记录表(handledRecord)
        _id:ObjectId
        info_id:ObjectId   告警记录logInfo的对应id
        name:(str) 处理人
        tag:(str) 处理事件
        time:(str) 处理时间
---
    任务表(tasks)---------主要有三种任务，分别是type：1，2，3
        _id：ObjectId
        app:(str) 项目代号
        name:(str) 项目名称
        type:(int)  1   -----轮询任务的类型
        timeCell:(int)  轮询的时间间隔，多久查询一次
        times:(int)  触发告警的次数限制
        params:(str)  查询的参数，前端配置参数内容按照键值方式，中间用，分隔，然后后端处理构造查询参数
        way:(list)    通知方式
            sms:(str)  短信通知
            email:(str)  邮件通知
        person:(list)    告警信息通知人
        pid:(str)     轮询任务的进程ID
        status:(int)   任务的启动/停止状态
            0：停止
            1：启动
---
    任务表(tasks)-----------主要有三种任务，分别type：1，2，3
        _id:ObjectId
        app:(str)   项目代号
        name:(str)  项目名称
        type:(int) 2  ---定期统计任务
        person:(list)  统计信息的邮件通知人
        pid:(str)  统计任务进程的id
        status:(int)：这个status状态是根据项目触发的，项目的统计任务开始和停止
            0:停止
            1:启动
        crontab:(str)  配置的crontab规则，指定触发发送统计邮件的时间
        interval:(int)
            1:日报，当前日期前一天的统计
            7:周报，当前日期前周的统计
            30:月报，当前日期前一个月的统计
---
    任务表(tasks)-----------主要有三种任务，分别type：1，2，3
        _id:ObjectId
        app:(str)   项目代号
        name:(str)  项目名称
        type:(int) 3  ---单次统计任务
        person:(list)  统计信息的邮件通知人
        pid:(str)  统计任务进程的id
        status:(int)：这个status状态是根据项目触发的，项目的统计任务开始和停止
            0:停止
            1:启动
        
    
    
               
        

