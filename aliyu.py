'''
阿里云盘签到
功能：自动签到，领取签到奖品，支持多账号（使用#分割token），支持青龙
到这里获取token：http://qr.ziyuand.cn/

cron： 1 1,12 1 * * *
by：cherwin
'''
import base64
import hashlib
import json
import os
import random
import time

import requests
from os import environ, path
from sys import exit
import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def load_send():
    global send, mg
    cur_path = path.abspath(path.dirname(__file__))
    if path.exists(cur_path + "/notify.py"):
        try:
            from notify import send
            print("加载通知服务成功！")
        except:
            send = False
            print("加载通知服务失败~")
    else:
        send = False
        print("加载通知服务失败~")


load_send()
send_msg = ''


def Log(cont):
    global send_msg
    print(cont)
    send_msg += f'{cont}\n'


REFRESHTOEKN_PATH = "ALYP_REFRESH_TOEKN.json"


def saveRefreeshToken(data):
    # 保存数据到文件
    if os.path.isfile(REFRESHTOEKN_PATH):
        with open(REFRESHTOEKN_PATH, 'r') as file:
            try:
                refresh_tokens = json.load(file)
            except:
                refresh_tokens = {}
    else:
        refresh_tokens = {}
    refresh_tokens.update(data)
    with open(REFRESHTOEKN_PATH, 'w') as file:
        json.dump(refresh_tokens, file)


def loadRefreshTokens():
    try:
        with open(REFRESHTOEKN_PATH, 'r') as file:
            file_content = file.read()
            if file_content:
                refresh_tokens = json.loads(file_content)
            else:
                refresh_tokens = {}
    except FileNotFoundError:
        refresh_tokens = {}

    return refresh_tokens


def is_last_day_of_month():
    today = datetime.date.today()
    next_month = today.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)
    return today == last_day


class AliDrive_CheckIn:
    def __init__(self, refresh_token, ali_reward):
        self.userAgent = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 D/C501C6D2-FAF6-4DA8-B65B-7B8B392901EB"
        self.refresh_token = refresh_token
        self.ali_reward = ali_reward
        self.file_id = ''
        self.headers = {
            "Content-Type": "application/json",
            "charset": "utf-8",
            "User-Agent": self.userAgent
        }

    def getToken(self):
        url = 'https://auth.aliyundrive.com/v2/account/token'
        body = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        response = s.post(url, headers=self.headers, json=body, verify=False)
        try:
            resp = response.json()
            if resp.get('code') == 'InvalidParameter.RefreshToken':
                Log('\nRefreshToken 有误请检查！(可能token失效了，到这里获取http://qr.ziyuand.cn)\n')
                return False
            else:
                self.aliYunPanToken = f'Bearer {resp.get("access_token", "")}'
                self.access_token = resp.get("access_token", "")
                self.aliYunPanRefreshToken = resp.get("refresh_token", "")
                print(f'refresh_token:{self.aliYunPanRefreshToken}')
                self.user_id = resp.get("user_id", "")
                self.headers['Authorization'] = self.aliYunPanToken
                Log(f">账号ID：【{self.user_id}】\n>获取token成功")
                self.getUserInfo()
                # # 保存数据到文件
                # saveData = {self.user_id: self.aliYunPanRefreshToken}
                # saveRefreeshToken(saveData)
                return True
        except:
            print(response.text)
            return False

    def getUserInfo(self):
        url = 'https://api.aliyundrive.com/adrive/v2/user/get'
        body = {
            "addition_data": {},
            "user_id": self.user_id
        }
        response = s.post(url, headers=self.headers, json=body, verify=False)
        try:
            resp = response.json()
            self.phone = resp.get("phone", "")
            self.phone = self.phone[:3] + '*' * 4 + self.phone[7:]
            Log(f">手机号：【{self.phone}】")
            # 保存数据到文件
            saveData = {self.phone: self.aliYunPanRefreshToken}
            saveRefreeshToken(saveData)
            return True
        except:
            print(response.text)

    def get_sign_in_list(self):
        sign_url = 'https://member.aliyundrive.com/v2/activity/sign_in_list?_rx-s=mobile}'
        sign_body = {'isReward': False}
        sign_res = s.post(sign_url, headers=self.headers, json=sign_body, verify=False)

        try:
            sign_resp = sign_res.json()
            result = sign_resp.get('result', {})
            self.sign_in_count = result.get('signInCount', 0)
            is_sign_in = result.get('isSignIn', False)

            if is_sign_in:
                Log(f'>签到成功！\n>已累计签到{self.sign_in_count}天！')
            else:
                Log(f'>今日已签到！\n>已累计签到{self.sign_in_count}天！')

            sign_in_infos = result.get('signInInfos', [])
            rewards_list = sign_in_infos[self.sign_in_count - 1].get('rewards', [])
            status = rewards_list[1].get('status', '')
            print(status)

            remind = rewards_list[1].get('remind', '')
            complete_status_list = ["verification", "finished", "end"]

            if status not in complete_status_list:
                self.handle_task(remind)
            else:
                print(f'任务【{remind}】已完成')
        except Exception as e:
            print(f"获取签到列表失败：{e}")

    def handle_task(self, task_name):
        print(f'开始【{task_name}】任务')
        if task_name == '接3次好运瓶即可领取奖励':
            self.bottle_fish()
        elif task_name == '订阅官方账号「阿里盘盘酱」即可领取奖励':
            self.follow_user()
        elif task_name == '上传10个文件到备份盘即可领取奖励':
            self.fileName = '签到任务文件_喜欢可以赞赏一波_谢谢.jpg'
            self.upload_files_to_drive(10)
        elif task_name == '备份10张照片到相册即可领取奖励':
            self.fileName = '签到任务文件_喜欢可以赞赏一波_谢谢.jpg'
            self.upload_files_to_drive(10, 'alibum')
        elif task_name == '播放1个视频30秒即可领取奖励':
            # pass
            self.get_videoList()
        else:
            print(f'>今日任务：{task_name}-暂不支持此任务，请手动完成！')
        time.sleep(5)

    ###############################文件上传任务开始###############################

    def upload_files_to_drive(self, num_files, drive_type='Default'):
        for i in range(num_files):
            self.get_user_drive_info(drive_type)
            time.sleep(1)

    def get_user_drive_info(self, drive_type):
        url = "https://api.aliyundrive.com/v2/drive/list_my_drives"
        response = s.post(url, headers=self.headers, json={})
        try:
            if response.status_code == 200:
                data = response.json()
                # print(data)
                drive_list = data.get("items", [])
                if drive_list != []:
                    index = None
                    for i, item in enumerate(drive_list):
                        if drive_type == 'alibum':
                            if item['drive_name'] == 'alibum':
                                index = i
                                break
                        else:
                            if item['drive_name'] == 'Default' and item['category'] == 'backup':
                                index = i
                                break
                    self.drive_id = drive_list[index]['drive_id']
                    print(f'当前drive ID:{self.drive_id}')
                if self.drive_id:
                    self.file_create(drive_type)
            else:
                print("获取用户云盘信息API请求失败")
        except Exception as e:
            print(f"获取用户云盘信息失败：{e}")

    def get_file_size(self, file_path):
        try:
            # 获取文件大小
            print(f'文件大小{os.path.getsize(file_path)}')
            return os.path.getsize(file_path)
        except OSError:
            return 0

    def get_file_hash(self, file_path):
        with open(file_path, 'rb') as f:
            buffer_size = 10 * 1024
            sha1 = hashlib.sha1()
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest().upper()

    def get_signTaskFileId(self):
        url = "https://api.aliyundrive.com/v2/file/search"
        json_data = {
            'drive_id': self.drive_id,
            'order_by': 'name ASC',
            'query': f'name = "{self.fileName}"',
        }
        response = s.post(url, headers=self.headers, json=json_data)
        data = response.json()

        try:
            if response.status_code == 200:
                fileList = data.get("items", [])
                if fileList:
                    print(f'找到签到任务文件id：{fileList[0]["file_id"]}')
                    print(f'执行覆盖上传')
                    return fileList[0]['file_id']
                else:
                    print(f'未找到签到任务文件')
            else:
                print("搜索文件API请求失败")
        except Exception as e:
            print(f"获取签到任务文件ID失败：{e}")

        return ''

    def file_create(self, type):
        self.filePath = f'./{self.fileName}'
        self.size = self.get_file_size(self.filePath)
        content_hash = self.get_file_hash(self.filePath)
        json_data = {
            'name': self.fileName,
            'type': 'file',
            'parent_file_id': 'root',
            'drive_id': self.drive_id,
            'check_name_mode': 'ignore',
            'size': self.size,
            "content_hash": content_hash,
            "content_hash_name": "sha1",
        }

        url = "https://api.aliyundrive.com/v2/file/create"
        if type == 'alibum':
            url = "https://api.aliyundrive.com/adrive/v2/biz/albums/file/create"
            json_data['proof_version'] = 'v1'
            json_data['proof_code'] = self._get_proof_code()
            json_data['content_type'] = 'image/jpeg'
            json_data['create_scene'] = 'album_autobackup'
            json_data['check_name_mode'] = 'auto_rename'

        if self.file_id == '':
            self.file_id = self.get_signTaskFileId()
        elif self.file_id != '':
            json_data['file_id'] = self.file_id

        response = s.post(url, headers=self.headers, json=json_data)
        data = response.json()

        try:
            if response.status_code == 201 or response.status_code == 200:
                rapid_upload = data.get('rapid_upload', False)
                self.file_id = data.get('file_id', '')
                if rapid_upload:
                    Log(f"文件秒传成功")
                    return "文件秒传成功"
                else:
                    part_info_list = data.get('part_info_list', [])
                    upload_url = part_info_list[0]['upload_url']
                    if type != 'alibum':
                        self.upload_id = data.get('upload_id', '')
                    if upload_url:
                        with open(self.filePath, 'rb') as f:
                            part_content = f.read(self.size)
                        response = s.put(upload_url, data=part_content)
                        if response.status_code != 200:
                            raise Exception(f"文件上传失败")
                        Log(f"文件上传成功")
                        self.file_complete()
            else:
                print(f"上传文件API请求失败{data}")
        except Exception as e:
            print(f"上传文件失败：{e}")

        return ''

    def file_complete(self):
        url = "https://api.aliyundrive.com/v2/file/complete"
        json_data = {
            'file_id': self.file_id,
            'upload_id': self.upload_id,
            'drive_id': self.drive_id
        }
        response = s.post(url, headers=self.headers, json=json_data)

        if response.status_code == 200:
            print(f"上传状态上报成功")
            # file_delete(file_id, drive_id)
        else:
            print("上传文件API请求失败")

    def file_delete(self, file_id, drive_id):
        url = "https://api.aliyundrive.com/v2/file/delete"
        json_data = {
            'file_id': file_id,
            'drive_id': drive_id
        }
        response = s.post(url, headers=self.headers, json=json_data)
        if response.status_code == 200:
            # print(data)
            print(f"删除文件成功")
        else:
            print("删除文件API请求失败")

    def _get_proof_code(self) -> str:
        """计算proof_code"""
        md5_int = int(hashlib.md5(self.access_token.encode()).hexdigest()[:16], 16)
        # file_size = os.path.getsize(file_path)
        offset = md5_int % self.size if self.size else 0
        if self.filePath.startswith('http'):
            # noinspection PyProtectedMember
            bys = self._session.get(self.filePath, headers={
                'Range': f'bytes={offset}-{min(8 + offset, self.size) - 1}'
            }).content
        else:
            with open(self.filePath, 'rb') as file:
                file.seek(offset)
                bys = file.read(min(8, self.size - offset))
        return base64.b64encode(bys).decode()

    ###############################文件上传任务结束###############################

    def bottle_fish(self):
        json_data = {}
        for i in range(3):
            response = requests.post('https://api.aliyundrive.com/adrive/v1/bottle/fish', headers=self.headers,
                                     json=json_data, verify=False)
            if response.status_code == 200:
                Log('接好运瓶成功！')
            else:
                print(response.text)

    def version_reward(self):
        json_data = {"code":"newVersion490Reward","rule":"all"}
        for i in range(3):
            response = requests.post('https://member.aliyundrive.com/v1/users/space_goods_reward?_rx-s=mobile', headers=self.headers,
                                     json=json_data, verify=False)
            if response.status_code == 200:
                Log('领取版本升级奖励成功！')
            else:
                print(response.text)

    def reward_sign(self, type, sign_in_count):
        json_data = {"signInDay": sign_in_count}
        if type == 'sign_in_reward':
            url = f'https://member.aliyundrive.com/v1/activity/{type}?_rx-s=mobile'
        else:
            url = f'https://member.aliyundrive.com/v2/activity/{type}?_rx-s=mobile'
        response = requests.post(url, headers=self.headers, json=json_data, verify=False)
        try:
            resp = response.json()
            if 'result' in resp and resp.get("result",None) != None:
                Log(f">{resp['result']['notice']}")
            elif 'success' in resp and resp.get("success",None) != None:
                Log(f">已领奖")
            else:
                Log(f">{resp['message']}")
        except:
            print(response.text)

    # 订阅阿里官方账号
    def follow_user(self):
        data = {"user_id": 'ec11691148db442aa7aa374ca707543c'}
        response = s.post('https://api.aliyundrive.com/adrive/v1/member/follow_user', headers=self.headers, json=data,
                          verify=False)
        if response.status_code == 200:
            Log('订阅成功！')
        else:
            print(response.text)

    # 获取最近视频列表
    def get_videoList(self):
        data = {}
        response = s.post('https://api.aliyundrive.com/adrive/v2/video/list', headers=self.headers, json=data,
                          verify=False)
        if response.status_code == 200:
            data = response.json()
            Video_list = data.get("items",False)
            if Video_list:
                Video_list_len = len(Video_list)
                for i in range(Video_list_len):
                    Video_info = Video_list[random.randint(0,Video_list_len-1)]
                    # print(f'当前Video_info:\n{Video_info}')
                    if Video_info.get("type", "") == 'file':
                        name = Video_info['name']
                        file_id = Video_info['file_id']
                        drive_id = Video_info['drive_id']
                        duration = Video_info['duration']
                        play_cursor = str(float(Video_info['play_cursor']) + 31)
                        print(f'待上传时间：{play_cursor}')
                        thumbnail = Video_info['thumbnail']
                        file_extension = Video_info['file_extension']
                        self.videoUpdate(drive_id,duration,file_extension,file_id,name,play_cursor,thumbnail)
                        break
            elif Video_list == []:
                self.fileName = '签到任务文件_视频.mp4'
                print('网盘没有视频文件，尝试上传任务视频，重新获取视频信息')
                self.upload_files_to_drive(1)
                self.get_videoList()

        else:
            print(response.text)

    # 获取最近视频列表
    def videoUpdate(self,drive_id,duration,file_extension,file_id,name,play_cursor,thumbnail):
        data = {
            "drive_id": drive_id,
            "duration": duration,
            "file_extension": file_extension,
            "file_id": file_id,
            "name":name,
            "play_cursor": play_cursor,
            "thumbnail": thumbnail
        }
        response = s.post('https://api.aliyundrive.com/adrive/v2/video/update', headers=self.headers, json=data,
                          verify=False)
        if response.status_code == 200:
            print('上传观看时间成功！')
        else:
            print(response.text)


    def join_team(self):
        check_team_data = {}
        check_team_res = s.post('https://member.aliyundrive.com/v1/activity/sign_in_team?_rx-s=mobile',
                                headers=self.headers, json=check_team_data, verify=False)
        try:
            resp = check_team_res.json()
            if resp['result'] != 'null':
                act_id = resp['result']['id']
                join_team_data = {"id": act_id, "team": "blue"}
                join_team_res = requests.post('https://member.aliyundrive.com/v1/activity/sign_in_team_pk?_rx-s=mobile',
                                              headers=self.headers, json=join_team_data, verify=False)
                try:
                    join_team_res = join_team_res.json()
                    if join_team_res['success']:
                        Log('>加入蓝色战队成功!')
                except:
                    print(join_team_res.text)
        except:
            print(check_team_res.text)

    def use_signCard(self):
        use_signCard_data = {}
        use_signCard_res = s.post('https://member.aliyundrive.com/v1/activity/complement_sign_in?_rx-s=mobile',
                                  headers=self.headers, json=use_signCard_data, verify=False)
        try:
            resp = use_signCard_res.json()
            if resp['code'] != 'BadRequest':
                Log('>补签成功！')
            else:
                Log(f">补签失败！原因：{resp['message']}")
        except:
            print(use_signCard_res.text)

    def main(self, indx):
        log_message = f"\n开始执行第【{indx + 1}】个账号--------------->>>>>"
        Log(log_message)
        current_day = datetime.datetime.now().day

        if self.getToken():
            self.get_sign_in_list()
  #新增领取版本奖励
            self.version_reward()

            if self.ali_reward:
                self.reward_sign('sign_in_reward', current_day)
                self.reward_sign('sign_in_task_reward', current_day)
            else:
                if not is_last_day_of_month():
                    Log(f'>今天是【{current_day}】日，您设置了不自动领取奖品，不自动领取')
                else:
                    Log('>今日为本月最后一天，默认领取所有奖品')
                  
                    for day in range(1, current_day + 1):
                        Log(f'开始领取【第{day}天】奖品')
                        self.reward_sign('sign_in_reward', day)
                        self.reward_sign('sign_in_task_reward', day)
                        time.sleep(1)

            self.use_signCard()
            # self.get_videoList()
        else:
            return False

def del_cash(file_path):
    try:
        # 删除文件
        os.remove(file_path)
        print("缓存文件删除成功")
        return True
    except FileNotFoundError:
        print("缓存文件不存在")
        return "缓存文件不存在"
    except Exception as e:
        print(f"缓存文件删除失败：{e}")
        return f"缓存文件删除失败：{e}"

#对比缓存与环境变量token长度
def len_comp(Cash,TOKEN,QL= False):
    global refresh_tokens,LEN
    Cash_Tokens = '#'.join(Cash.values())
    TOKEN_LEN = len(Cash_Tokens.split('#'))
    TOKENS = Cash_Tokens.split('#')
    if QL:
        parts = ENV.split('&')
        ENV_TOKEN = []
        for part in parts:
            ENV_TOKEN.extend(part.split('#'))
        # ENV_TOKEN = TOKEN.split('#')
    else:
        ENV_TOKEN = TOKEN.split('#')
    ENV_TOKEN_LEN = len(ENV_TOKEN)
    if ENV_TOKEN_LEN != TOKEN_LEN:
        print('***缓存freshToken长度与环境变量长度不一致，使用【环境变量】')
        print('***准备删除缓存')
        del_cash(REFRESHTOEKN_PATH)
        refresh_tokens = ENV_TOKEN
        LEN = ENV_TOKEN_LEN
    else:
        print('***缓存freshToken长度与环境变量长度一致，使用【缓存】')
        refresh_tokens = TOKENS
        LEN = TOKEN_LEN
# 检测并更新脚本函数
def detect_and_update_script(local_script_path, remote_script_url):
    # 下载远程脚本并保存到本地
    def download_remote_script():
        response = requests.get(remote_script_url)
        with open(local_script_path, "wb") as file:
            file.write(response.content)

    # 删除本地脚本
    def delete_local_script():
        os.remove(local_script_path)

    # 计算文件的哈希值
    def calculate_hash(file_path):
        with open(file_path, "rb") as file:
            content = file.read()
            return hashlib.sha256(content).hexdigest()

    # 检查远程脚本是否需要更新
    def check_for_updates():
        try:
            response = requests.get(remote_script_url)
            remote_script_content = response.text

            local_script_hash = calculate_hash(local_script_path)
            remote_script_hash = hashlib.sha256(remote_script_content.encode("utf-8")).hexdigest()

            return local_script_hash != remote_script_hash
        except Exception as e:
            print(f"检查更新失败：{e}")
            return False

    # 执行更新操作
    def update():
        print('正在更新脚本...')
        download_remote_script()

    # 检查是否需要更新并执行相应操作
    if check_for_updates():
        AUTO_UPDATE = environ.get("ALYP_UPDATE") if environ.get("ALYP_UPDATE") else False
        if AUTO_UPDATE:
            print(">>>>>>>发现新版本的脚本，准备更新...")
            update()
        else:
            print(">>>>>>>发现新版本的脚本，您未启用自动更新，如需启用请定义变量export ALYP_UPDATE = 'True'")

    else:
        print("脚本无需更新")
if __name__ == '__main__':

    # 检查更新
    local_script_path = os.path.abspath(__file__)
    remote_script_url = "http://pan.ziyuand.cn/d/%E8%BD%AF%E4%BB%B6%E8%B5%84%E6%BA%90%E7%B1%BB/%E8%84%9A%E6%9C%AC/ALYP.py"
    detect_and_update_script(local_script_path, remote_script_url)
    refresh_token = ''
    refresh_tokens = ''
    LEN = 0
    Cash_Tokens = loadRefreshTokens()
    ENV = environ.get("ALYP") if environ.get("ALYP") else False
    if Cash_Tokens:
        print('******检测到缓存freshToken存在，如不使用缓存freshToken请删除ALYP_REFRESHTOEKN.json文件')
    else:
        print('******未检测到缓存freshToken')

    if refresh_token == '':
        if not ENV:
            print("******未填写 ALYP变量 青龙可在环境变量设置 ALYP 或者在本脚本文件上方将获取到的refresh_token填入refresh_token中")
            exit(0)
        # parts = ENV.split('&')
        # sub_strings = []
        # for part in parts:
        #     sub_strings.extend(part.split('#'))
        if '&' in ENV:
            len_comp(Cash_Tokens, ENV,True)
        else:
            len_comp(Cash_Tokens, ENV)
    else:
        len_comp(Cash_Tokens, refresh_token)

    #自动领取开关
    ali_reward = environ.get("ali_reward") if environ.get("ali_reward") else True
    if ali_reward:
        print('******默认自动领取奖品,如需关闭自动领取请定义变量：export ali_reward="False"\n******默认自动补签')
    else:
        print('******设置了不自动领取奖品')
    print(f'******当前使用token：\n{refresh_tokens}')
    if LEN > 0:
        print(f"\n>>>>>>>>>>共获取到{LEN}个账号<<<<<<<<<<")
        for indx, ck in enumerate(refresh_tokens):
            s = requests.session()
            s.verify = False
            Sign = AliDrive_CheckIn(ck, ali_reward).main(indx)
            if not Sign: continue
        send('阿里云盘签到通知', send_msg)
