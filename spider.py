#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author:zj time: 2019/7/29 19:44
import re
import ast
from queue import Queue

import requests
from threading import Thread
from scrapy import Selector
from urllib.parse import urljoin
from datetime import datetime

from csdn_spider.models import *

domain = 'https://bbs.csdn.net'
list_queue = Queue()
topic_queue = Queue(10)
author_queue = Queue(10)

def get_nodes_list():
	response = requests.get('https://bbs.csdn.net/dynamic_js/left_menu.js?csdn').text
	left_menu = re.search('forumNodes: (.*])', response)
	if left_menu:
		nodes_str = left_menu.group(1).replace('null', "None")
		nodes_list = ast.literal_eval(nodes_str)
		return nodes_list
	return []


url_list = []
def get_nodes_url(nodes_list):
	for item in nodes_list:
		if "url" in item:
			url_list.append(item['url'])
			if 'children' in item:
				get_nodes_url(item['children'])

def get_level_one_url(nodes_list):
	level_one_url = []
	for item in nodes_list:
		if "url" in item:
			level_one_url.append(item['url'])
	return level_one_url

def get_last_url():
	nodes_list = get_nodes_list()
	get_nodes_url(nodes_list)
	level_one_list = get_level_one_url(nodes_list)
	last_url = []
	for url in url_list:
		if url not in level_one_list:
			last_url.append(url)
	return last_url

def get_all_url():
	last_url = get_last_url()
	all_url = []
	for url in last_url:
		all_url.append(urljoin(domain, url))
		all_url.append(urljoin(domain, url+'/closed'))
		all_url.append(urljoin(domain, url+'/recommend'))
	return all_url


class ParseTopicThread(Thread):
	def run(self):
		while 1:
			if self.topic_queue.empty():
				break
			answer_url = topic_queue.get()
			print('开始爬取topic:{}'.format(answer_url))
			topic_id = answer_url.split('/')[-1]
			response = requests.get(answer_url).text
			html = Selector(text=response)
			all_divs = html.xpath('//div[@class="bbs_detail_wrap"]/div[starts-with(@id, "post-")]')
			topic_item = all_divs[0]
			topic_content = topic_item.xpath(".//div[@class='post_body post_body_min_h']").extract()
			topic_jyl = topic_item.xpath('.//div[@class="close_topic"]/text()').extract()[0]
			jtl_search = re.search('(\d+)%', topic_jyl)
			jtl = 0
			if jtl_search:
				jtl = jtl_search.group(1)
			praise_nums = topic_item.xpath('.//div[@class="control_l fl"]//em/text()').extract()
			existed_topics = Topic.select().where(Topic.id==topic_id)
			if existed_topics:
				topic = existed_topics[0]
				if topic_content:
					topic.content = topic_content
				topic.jtl = jtl
				if praise_nums:
					topic.praise_nums = int(praise_nums[0])
				topic.save()

			for answer_item in all_divs[1:]:
				answer = Answer()
				id = answer_item.xpath('./@data-post-id').extract()[0]
				answer.id = id
				answer_info = answer_item.xpath('.//div[@class="nick_name"]/a/@href').extract()[0]
				answer_id = answer_info.split('/')[-1]
				answer.author = answer_id
				answer_content = answer_item.xpath(".//div[@class='post_body post_body_min_h']").extract()
				if answer_content:
					answer.content = answer_content
				create_time = answer_item.xpath('.//div[@class="control_l fl"]/label[2]/text()').extract()[0]
				create_time = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S')
				praise_nums = answer_item.xpath('.//div[@class="control_l fl"]//em/text()').extract()[0]
				answer.topic_id = topic_id
				answer.create_time = create_time
				answer.praise_nums = int(praise_nums)

				existed_Authors = Answer.select().where(Answer.id == id)
				if existed_Authors:
					answer.save()
				else:
					answer.save(force_insert=True)

			next_page = html.xpath(
				'//a[@class="pageliststy next_page"]/@href').extract()
			if next_page:
				next_page = urljoin(domain, next_page[0])
				topic_queue.put(next_page)


class ParseAuthorThread(Thread):
	def run(self):
		while 1:
			if self.author_queue.empty():
				break
			author_url = author_queue.get()
			print('开始爬取用户信息：{}'.format(author_url))
			author = Author()
			headers = {
				"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.108 Safari/537.36"
			}
			response = requests.get(author_url, headers=headers).text
			html = Selector(text=response)
			author_id = author_url.split('/')[-1]
			author.id = author_id
			author_name = html.xpath('//p[@class="lt_title"]/text()[3]').extract()[0]
			author.name = author_name
			nums = html.xpath('//div[@class="me_chanel_det_item access"]//span/text()').extract()
			blog_nums = nums[0].strip()
			author.blog_nums = blog_nums
			rate = nums[1].strip()
			author.rate = rate
			desc = html.xpath('//div[@class="description clearfix"]/p/text()').extract()
			if desc:
				desc = desc[0].strip()
				author.describe = desc
			fans = html.xpath('//div[@class="fans"]//span/text()').extract()[0].strip()
			author.fans_nums = fans
			following_nums = html.xpath('//div[@class="att"]//span/text()').extract()[0].strip()
			author.following_nums = following_nums

			existed_Authors = Author.select().where(Author.id == author_id)
			if existed_Authors:
				author.save()
			else:
				author.save(force_insert=True)


class ParseListThread(Thread):
	def run(self):
		while 1:
			if self.list_queue.empty():
				break
			topic_url = list_queue.get()
			print('开始爬取：{}'.format(topic_url))

			topic = Topic()
			response = requests.get(topic_url).text
			html = Selector(text=response)
			all_trs = html.xpath('//table[@class="forums_tab_table"]/tbody/tr')
			for tr in all_trs:
				status = tr.xpath('./td[1]/span/text()').extract()[0]
				topic.status = status
				score = tr.xpath('./td[2]/em/text()').extract()
				if score:
					topic.score = int(score[0])
				topic_title = tr.xpath('./td[3]//text()').extract()
				topic_title = ''.join(topic_title)
				topic.title = topic_title
				topic_url = tr.xpath('./td[3]/a[contains(@class, "forums_title")]/@href').extract()[0]
				author = tr.xpath('./td[4]/a/text()').extract()[0]
				topic.author = author
				create_time = tr.xpath('./td[4]/em/text()').extract()[0]
				create_time = datetime.strptime(create_time, '%Y-%m-%d %H:%M')
				topic.create_time = create_time
				author_url = tr.xpath('./td[4]/a/@href').extract()[0]
				topic.id = int(topic_url.split('/')[-1])
				answer_info = tr.xpath('./td[5]/span/text()').extract()
				if answer_info:
					answer_nums = answer_info[0].split('/')[0]
					click_nums = answer_info[0].split('/')[1]
					topic.answer_nums = int(answer_nums)
					topic.click_nums = int(click_nums)
				last_time = tr.xpath('./td[6]/em/text()').extract()[0]
				last_time = datetime.strptime(last_time, '%Y-%m-%d %H:%M')
				topic.last_answer = last_time

				existed_topics = Topic.select().where(Topic.id==topic.id)
				if existed_topics:
					topic.save()
				else:
					topic.save(force_insert=True)

				topic_queue.put(urljoin(domain, topic_url))
				author_queue.put(urljoin(domain, author_url))

			next_page = html.xpath('//a[@class="pageliststy next_page"]/@href').extract()
			if next_page:
				next_page = urljoin(domain, next_page[0])
				list_queue.put(next_page)



if __name__ == '__main__':
	all_url = get_all_url()
	for url in all_url:
		list_queue.put(url)

	t1 = ParseListThread()
	t2 = ParseTopicThread()
	t3 = ParseAuthorThread()

	t1.start()
	t2.start()
	t3.start()

