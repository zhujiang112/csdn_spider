#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author:zj time: 2019/7/29 16:56
from peewee import *

db = MySQLDatabase("python_spider", host="127.0.0.1", port=3306, user="root", password="zj19960728")

class BaseModel(Model):
	class Meta:
		database = db


class Topic(BaseModel):
	id = IntegerField(primary_key=True)       # 页面id
	title = CharField()						  # 标题
	content = TextField(default="")			  # 内容
	author = CharField()					  # 作者
	create_time = DateTimeField()			  # 创建时间
	answer_nums = IntegerField(default=0)     # 回复数
	click_nums = IntegerField(default=0)	  # 点击数
	praise_nums = IntegerField(default=0)     # 点赞数
	jtl = IntegerField(default=0)    		  # 结帖率
	score = IntegerField(default=0)			  # 分数
	status = CharField()   					  # 状态
	last_answer = DateTimeField()			  # 最后回复时间


class Answer(BaseModel):
	id = IntegerField(primary_key=True)  	  # 回复id
	topic_id = IntegerField()				  # 帖子id
	author = CharField()					  # 作者id
	content = TextField(default="")			  # 回复内容
	create_time = DateTimeField()			  # 回复时间
	praise_nums = IntegerField()			  # 点赞数


class Author(BaseModel):
	name = CharField()									# 作者
	id = CharField(primary_key=True, max_length=100)	# 作者id
	blog_nums = IntegerField()    						# 博文数
	rate = CharField()									# 排名
	describe = TextField(null=True)						# 个人描述
	fans_nums = IntegerField()							# 粉丝数
	following_nums = IntegerField()						# 关注数


if __name__ == '__main__':
	db.create_tables([Topic, Answer, Author])