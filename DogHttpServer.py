# -*- coding:utf-8 -*-

import base64
import copy
import json
import pymysql as mysql
import numpy as np
import os
import sys
import tornado.ioloop
import tornado.web
from PIL import Image
from keras.applications.inception_v3 import preprocess_input
from keras.models import load_model


# 数据库参数设置：
from keras.preprocessing import image

model = load_model("dog_predict.model")
mysql_host = "127.0.0.1"
mysql_user = "root"
mysql_password = "root"
mysql_database_name = "dog"


# 连接数据库
def database_connect():
    return mysql.connector.connect(
        host=mysql_host,
        user=mysql_user,
        password=mysql_password,
        db=mysql_database_name)

'''
# 初始化数据库表函数
def init_database():
    db = None
    try:
        # 打开数据库连接
        db = database_connect()
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()
        # 如果数据表已经存在使用 execute() 方法删除表。
        cursor.execute("DROP TABLE IF EXISTS sports;")
        cursor.execute("DROP TABLE IF EXISTS friends;")
        cursor.execute("DROP TABLE IF EXISTS users;")
        # 创建用户表users
        sql = """CREATE TABLE users (
                        user_id CHAR(22) PRIMARY KEY,
                        password CHAR(22),
                        sex CHAR(22),
                        age INT,
                        height DOUBLE,
                        weight DOUBLE,
                        fat_rate DOUBLE,
                        target_weight DOUBLE,
                        target_fat_rate DOUBLE)
                        CHARACTER SET = utf8;"""
        cursor.execute(sql)
        # 创建运动数据表sports
        sql = """CREATE TABLE sports (
                        sports_id INT AUTO_INCREMENT,
                        user_id CHAR(22),
                        full_range_longitude_latitude BLOB,
                        full_range_speed DOUBLE,
                        full_range_steps INT,
                        full_range_distance DOUBLE,
                        start_time DATETIME,
                        end_time DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users(user_id),
                        PRIMARY KEY(sports_id))
                        CHARACTER SET = utf8;"""
        cursor.execute(sql)
        # 创建好友表friends
        sql = """CREATE TABLE friends (
                        user_id CHAR(22) PRIMARY KEY,
                        longitude DOUBLE,
                        latitude DOUBLE,
                        update_time DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users(user_id))
                        CHARACTER SET = utf8;"""
        cursor.execute(sql)
    except Exception as e:
        print(e)
        print("Database init failed!")
        sys.exit(1)
    finally:
        if db is not None:
            db.close()


# 字典的值转字符串列表
def dic_values_to_string_list(dic_values):
    string_list = []
    for value in dic_values:
        if isinstance(value, str):
            string_list.append("'" + str(value) + "'")
        else:
            string_list.append(str(value))
    return string_list


# 字典的键值对转"k=v"形式字符串列表
def dic_to_string_list(dic):
    string_list = []
    for k, v in dic.items():
        if isinstance(v, str):
            string_list.append(k + "='" + str(v) + "'")
        else:
            string_list.append(k + "=" + str(v))
    return string_list


# 维护数据库中用户表
def users(data, train=0):
    db = None
    try:
        # 打开数据库连接
        db = database_connect()
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()

        if train == 0:
            method = data.pop("method")
        else:
            method = "check"
        # 用户注册
        if method == "signup":
            to_insert = dic_values_to_string_list(data.values())
            sql = "INSERT INTO users ({}) VALUES ({});".format(
                ",".join(data.keys()),
                ",".join(to_insert))
            print(sql)
            cursor.execute(sql)
            db.commit()
            detail = {}
        # 更新用户
        elif method == "update":
            user_id = data.pop("user_id")
            to_update = dic_to_string_list(data)
            sql = "UPDATE users SET {} WHERE user_id = '{}';".format(
                ",".join(to_update),
                user_id)
            print(sql)
            cursor.execute(sql)
            db.commit()
            detail = {}
        # 检查用户
        elif method == "check":
            user_id = data.pop("user_id")
            sql = "SELECT * FROM users WHERE user_id = '{}';".format(user_id)
            print(sql)
            cursor.execute(sql)
            record = cursor.fetchone()
            if train != 0:
                return record
            if record is not None:
                detail = {'user_id': record[0],
                          'password': record[1],
                          'sex': record[2],
                          'age': record[3],
                          'height': record[4],
                          'weight': record[5],
                          'fat_rate': record[6],
                          'target_weight': record[7],
                          'target_fat_rate': record[8]}
            else:
                return "no", {"user_id": user_id}
        # method不存在
        else:
            return "no", {"method": method}

    except Exception as e:
        # 发生错误时回滚
        db.rollback()
        print(e)
        return "no", "{}".format(e)
    finally:
        if db is not None:
            db.close()
    return "yes", detail


# 维护数据库中运动表
def sports(data):
    db = None
    try:
        # 打开数据库连接
        db = database_connect()
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()

        method = data.pop("method")
        # 增加运动记录
        if method == "add":
            full_range_ll = data.pop("full_range_longitude_latitude")
            serialized = json.dumps(full_range_ll)
            encrypted = base64.b64encode(serialized, 'utf-8')
            to_insert_values = dic_values_to_string_list(data.values())
            to_insert_values.append("'" + encrypted + "'")
            to_insert_keys = data.keys()
            to_insert_keys.append("full_range_longitude_latitude")
            sql = "INSERT INTO sports ({}) VALUES({});".format(
                ",".join(to_insert_keys),
                ",".join(to_insert_values))
            print(sql)
            cursor.execute(sql)
            db.commit()
            detail = {}
        # 查找运动记录
        elif method == "check":
            results = []
            user_id = data.pop("user_id")
            sql = "SELECT * FROM sports WHERE user_id = '{}';".format(user_id)
            print(sql)
            cursor.execute(sql)
            records = cursor.fetchall()
            for record in records:
                result = {
                    'full_range_longitude_latitude':
                        json.loads(base64.b64decode(record[2])),
                    'full_range_speed': record[3],
                    'full_range_steps': record[4],
                    'full_range_distance': record[5],
                    'start_time': str(record[6]),
                    'end_time': str(record[7])
                }
                results.append(copy.copy(result))
            db.commit()
            detail = {'user_id': user_id, 'sports_record': results}
        # method不存在
        else:
            return "no", {"method": method}

    except Exception as e:
        # 发生错误时回滚
        db.rollback()
        print(e)
        return "no", "{}".format(e)
    finally:
        if db is not None:
            db.close()
    return "yes", detail


# 维护数据库中好友表
def friends(data):
    db = None
    try:
        # 打开数据库连接
        db = database_connect()
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()

        method = data.pop("method")
        # 添加或更新用户位置
        if method == "update":
            user_id = data["user_id"]
            sql = "SELECT * FROM friends WHERE user_id = '{}';".format(user_id)
            print(sql)
            cursor.execute(sql)
            records = cursor.fetchall()
            if len(records) == 0:
                to_insert = dic_values_to_string_list(data.values())
                sql = "INSERT INTO friends ({}) VALUES ({});".format(
                    ",".join(data.keys()),
                    ",".join(to_insert))
                print(sql)
                cursor.execute(sql)
                db.commit()
                detail = {}
            else:
                data.pop("user_id")
                to_update = dic_to_string_list(data)
                sql = "UPDATE friends SET {} WHERE user_id = '{}';".format(
                    ",".join(to_update),
                    user_id)
                print(sql)
                cursor.execute(sql)
                db.commit()
                detail = {}
        # 获取用户位置
        elif method == "check":
            sql = "SELECT * FROM friends;"
            print(sql)
            cursor.execute(sql)
            records = cursor.fetchall()
            results = []
            for record in records:
                result = {
                    'user_id': record[0],
                    'longitude': record[1],
                    'latitude': record[2],
                    'update_time': str(record[3])
                }
                results.append(copy.copy(result))
            db.commit()
            detail = {'friends': results}
        # method不存在
        else:
            return "no", {"method": method}

    except Exception as e:
        # 发生错误时回滚
        db.rollback()
        print(e)
        return "no", "{}".format(e)
    finally:
        if db is not None:
            db.close()
    return "yes", detail


# 推荐系统
def recommends(data):
    record = users(data, train=1)
    return None
    # return recommends_system.recommend(record)


# 综合信息
def multi_info(data):
    db = None
    detail = {}
    try:
        # 打开数据库连接
        db = database_connect()
        # 使用cursor()方法获取操作游标
        cursor = db.cursor()

        user_id = data["user_id"]
        date = data["date"]
        # 查询用户数据
        sql_user = "select weight, fat_rate, target_weight, target_fat_rate from users WHERE user_id = '{}';".format(
            user_id)
        # 查询某用户当天统计数据
        sql_date = "select SUM(full_range_distance), CAST(SUM(full_range_steps) AS SIGNED)  \
                       from sports  \
                       where user_id = '{}' and to_days(start_time) = to_days('{}')  \
                       GROUP BY user_id;".format(user_id, date)
        print(sql_user)
        print(sql_date)

        cursor.execute(sql_user)
        record_user = cursor.fetchall()
        if len(record_user) > 0:
            detail['weight'] = record_user[0][0]
            detail['fat_rate'] = record_user[0][1]
            detail['target_weight'] = record_user[0][2]
            detail['target_fat_rate'] = record_user[0][3]

            cursor.execute(sql_date)
            record_date = cursor.fetchall()
            if len(record_date) > 0:
                detail['distance'] = record_date[0][0]
                detail['steps'] = record_date[0][1]

                cursor.close()
                db.close()
            (status, detail_recommend) = recommends({"user_id": user_id})
            detail.update(detail_recommend)

    except Exception as e:  # 发生错误时回滚
        db.rollback()
        print(e)
        return "no", "{}".format(e)
    finally:
        if db is not None:
            db.close()
        return "yes", detail  # JSON REST服务处理
'''


def predict(model, img, target_size=(229, 229)): #fixed size for InceptionV3 architecture
  """Run model prediction on image
  Args:
    model: keras model
    img: PIL format image
    target_size: (w,h) tuple
  Returns:
    list of predicted labels and their probabilities
  """
  if img.size != target_size:
    img = img.resize(target_size)

  x = image.img_to_array(img)
  x = np.expand_dims(x, axis=0)
  x = preprocess_input(x)
  preds = model.predict(x)
  return preds[0]


def what_dog(data):
    detail = None
    try:
        image = base64.b64decode(data["image"])
        tmp_path = "tmp.jpg"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        with open(tmp_path, 'wb') as f:
            f.write(image)
        image = Image.open(tmp_path)
        labels = (u"博美", u"吉娃娃", u"哈士奇", u"斑点狗", u"斗牛犬", u"杜宾犬", u"柴犬", u"藏獒", u"边牧", u"金毛")
        preds = predict(model, image)
        print(preds)
        if preds is not None:
            first_index = np.where(preds == np.max(preds))[0]
            dog_name = labels[first_index[0]]
            detail = {"dog_name": dog_name}
        else:
            return "no", {}
    except Exception as e:
        print(e)
        return "no", "{}".format(e)
    finally:
        return "yes", detail


class MainHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    def get(self):
        self.set_header("Content-Type", "application/json")
        data = {"status": "yes"}
        in_json = json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False)
        self.write(in_json)

    def post(self):
        data = json.loads(self.request.body.decode("utf-8"))
        status = "no"
        detail = None

        # 判断消息类型
        message = data.pop("message")
        if message == "what_dog":
            (status, detail) = what_dog(data)

        self.set_header("Content-Type", "application/json")
        data = {"status": status, "detail": detail}
        in_json = json.dumps(
            data, indent=4, ensure_ascii=False)
        self.write(in_json)
        print(in_json)


def make_app():
    return tornado.web.Application(
        [(r"/messages.*", MainHandler), ])


def main():
    app = make_app()
    app.listen(10086)
    #init_database()
    print("start serving...")
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
