#include <stdio.h>
#include <string>
#include <fstream>
#include <filesystem>
#include<iostream>
#include <direct.h>
#include"curl/curl.h"
#include <WinSock2.h>
#include <Windows.h>
#include "base64_utils.h"
#include <mysql.h>
#include  "crow.h"
#include <unordered_map>
#include <mutex>
#include <thread>
#include <chrono>





using namespace std;
std::unordered_map<int, int> user_status; 
// 全局哈希表，用于存储用户ID和WebSocket连接
std::unordered_map<long long, crow::websocket::connection*> connections;
std::unordered_map<long long, crow::websocket::connection*>RTC_connections;
std::mutex connections_mutex;
std::mutex RTC_connections_mutex;

MYSQL mysql;    // 全局数据库句柄



// 初始化数据库连接
bool init_db() {
    mysql_init(&mysql);
    mysql_options(&mysql, MYSQL_SET_CHARSET_NAME, "gbk");
    if (mysql_real_connect(&mysql, "127.0.0.1", "root", "xukaizhe1006", "chat", 3306, NULL, 0) == NULL) {
        cout << "错误原因: " << mysql_error(&mysql) << endl;
        cout << "连接失败!" << endl;
        return false;
    }
    cout << "连接成功" << endl;
    return true;
}

// 关闭数据库连接
void close_db() {
    mysql_close(&mysql);
}

// 用户认证函数
bool login(const std::string& account, const std::string& password) {
    std::string query = "SELECT * FROM user WHERE id='" + account + "' AND password='" + password + "';";

    int ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        cout << "查询失败: " << mysql_error(&mysql) << endl;
        return false;
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    bool authenticated = (mysql_num_rows(res) > 0);
    mysql_free_result(res);
    return authenticated;
}


bool registerUser(const std::string& username, const std::string& password, crow::json::wvalue& response) {
    // 插入新用户并获取生成的ID
    std::string insert_query = "INSERT INTO user (username, password) VALUES ('" + username + "', '" + password + "')";
    int ret = mysql_query(&mysql, insert_query.c_str());
    if (ret != 0) {
        cout << "插入失败: " << mysql_error(&mysql) << endl;
        return false;
    }
    int user_id = mysql_insert_id(&mysql);
    
    // 创建用户文件夹
    std::string folderPath = "..\\\\user\\\\" + std::to_string(user_id);
    std::wstring wFolderPath(folderPath.begin(), folderPath.end());
    
    string command;
    command = "mkdir " + folderPath;
    system(command.c_str());
    
    if (CreateDirectory(wFolderPath.c_str(), NULL) || ERROR_ALREADY_EXISTS == GetLastError()) {
        std::cout << "目录创建成功或已存在: " << folderPath << std::endl;
    }
    else {
        std::cerr << "无法创建目录: " << folderPath << " 错误: " << GetLastError() << std::endl;
        return false;
    }

    // 复制默认头像文件内容到用户文件夹中的avatar.txt文件
    std::ifstream src("mo_avatar.txt", std::ios::binary);
    if (!src) {
        std::cerr << "无法打开源文件: mo_avatar.txt" << std::endl;
        return false;
    }

    std::ofstream dst(folderPath + "\\avatar.txt", std::ios::binary);
    if (!dst) {
        std::cerr << "无法创建目标文件: " << folderPath + "\\avatar.txt" << std::endl;
        return false;
    }

    dst << src.rdbuf();
    src.close();
    dst.close();

    // 更新数据库中的头像路径
    std::string avatar_path = folderPath + "\\\\avatar.txt";
    std::string update_query = "UPDATE user SET avatar_path = '" + avatar_path + "' WHERE id = " + std::to_string(user_id);

    ret = mysql_query(&mysql, update_query.c_str());
    if (ret != 0) {
        std::cerr << "更新头像路径失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }

    // 返回用户ID
    response["user_id"] = user_id;
    return true;
}


//更新用户头像
void update_avatar(long long user_id, const std::string& avatar) {
    std::string query = "select avatar_path from user where id =" + std::to_string(user_id);
    if (mysql_query(&mysql, query.c_str())) {
        std::cerr << "UPDATE failed. Error: " << mysql_error(&mysql) << std::endl;
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    MYSQL_ROW row = mysql_fetch_row(res);
    if (row) {
        std::cout << "Result: " << (row[0] ? row[0] : "NULL") << std::endl;
        std::string filePath = row[0];

        // 将Base64编码的头像数据写入文件
        std::ofstream file(filePath);
        if (file.is_open()) {
            file << avatar;
            file.close();
            std::cout << "Avatar updated successfully.\n";
        }
        else {
            std::cerr << "Failed to open file: " << filePath << "\n";
        }
    }
    mysql_free_result(res);
}


//获取头像
std::string get_avatar(long long user_id) {
    std::string query = "select avatar_path from user where id =" + std::to_string(user_id);
    if (mysql_query(&mysql, query.c_str())) {
        std::cerr << "get failed. Error: " << mysql_error(&mysql) << std::endl;
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    MYSQL_ROW row = mysql_fetch_row(res);
    std::string base64_string;
    if (row) {
        std::cout << "Result: " << (row[0] ? row[0] : "NULL") << std::endl;
        std::ifstream file(row[0]);
        if (file.is_open()) {
            while (getline(file, base64_string)) {
            }
            file.close();
        }
        else {
            std::cerr << "Failed to open file "<< "\n";
        }
    }
    mysql_free_result(res);
    return base64_string;
}

// 更新好友关系表中的 last_message_time
void update_last_message_time(int sender_id, int receiver_id) {
    std::string query = "UPDATE friends SET last_message_time = NOW() WHERE (user_id = " + std::to_string(sender_id) + " AND friend_id = " + std::to_string(receiver_id) + ") OR (user_id = " + std::to_string(receiver_id) + " AND friend_id = " + std::to_string(sender_id) + ")";
    if (mysql_query(&mysql, query.c_str())) {
        std::cerr << "UPDATE failed. Error: " << mysql_error(&mysql) << std::endl;
    }
}


// 存储消息函数
void save_message(long long sender, long long receiver, const std::string& message) {
    std::string query = "INSERT INTO message_wait (sender, receiver, message) VALUES (" + std::to_string(sender) + ", " + std::to_string(receiver) + ", '" + message + "');";
    if (mysql_query(&mysql, query.c_str())) {
        std::cerr << "INSERT failed. Error: " << mysql_error(&mysql) << std::endl;
    }
    update_last_message_time(sender, receiver);
}


void send_saved_message(long long receiver) {
    std::string query = "SELECT id, sender, message FROM message_wait where receiver = " + std::to_string(receiver) + " order by time desc;";
    if (mysql_query(&mysql, query.c_str())) {
        std::cerr << "SELECT failed. Error: " << mysql_error(&mysql) << std::endl;
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    MYSQL_ROW row;
    std::lock_guard<std::mutex> lock(connections_mutex);
    auto it = connections.find(receiver);
    if (it != connections.end()) {
        while ((row = mysql_fetch_row(res))) {
            string id = row[0];
            long long sender_id = std::stoll(row[1]);
            std::string message = row[2];
            crow::json::wvalue response;
            response["sender"] = sender_id;
            response["message"] = message;
            it->second->send_text(dump(response));

            std::string delete_query = "DELETE FROM message_wait WHERE id = " + id + ";";
            if (mysql_query(&mysql, delete_query.c_str())) {
                std::cerr << "DELETE failed. Error: " << mysql_error(&mysql) << std::endl;
            }

            std::cout << "Message sent to user ID " << receiver << ": " << message << std::endl;
        }
    }
    mysql_free_result(res);
}


// 获取好友列表函数
crow::json::wvalue get_friends_list(int user_id) {
    std::string query = "SELECT u.id, u.username, s.status FROM user u JOIN friends f ON u.id = f.friend_id LEFT JOIN user_status s ON u.id = s.user_id WHERE f.user_id = " + std::to_string(user_id) + " ORDER BY f.last_message_time DESC";
    if (mysql_query(&mysql, query.c_str())) {
        std::cerr << "SELECT failed. Error: " << mysql_error(&mysql) << std::endl;
        return {};
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    MYSQL_ROW row;
    crow::json::wvalue friends_list;
    int i = 0;
    while ((row = mysql_fetch_row(res))) {
        friends_list[i]["user_id"] = std::stoi(row[0]);
        friends_list[i]["username"] = row[1];
        friends_list[i]["status"] = row[2] ? row[2] : "0";
        i++;
    }
    mysql_free_result(res);
    return friends_list;
}


// 更新用户状态函数
void update_user_status(long long user_id, int status) {
    std::string query = "INSERT INTO user_status (user_id, status) VALUES (" + std::to_string(user_id) + ", " + std::to_string(status) + ") ON DUPLICATE KEY UPDATE status = " + std::to_string(status) + "; ";
    if (mysql_query(&mysql, query.c_str())) {
        std::cerr << "UPDATE failed. Error: " << mysql_error(&mysql) << std::endl;
    }
}


bool sendFriendRequest(const long long& sender, const long long& receiver) {
    // 检查接收者是否存在
    std::string query = "SELECT COUNT(*) FROM user WHERE id=" + std::to_string(receiver) + ";";
    int ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "查询失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    MYSQL_ROW row = mysql_fetch_row(res);
    int receiverExists = std::stoi(row[0]);
    mysql_free_result(res);
    if (receiverExists == 0) {
        std::cout << "接收者不存在" << std::endl;
        return false;
    }
    // 检查两人是否已经是好友
    query = "SELECT COUNT(*) FROM friends WHERE (user_id=" + std::to_string(sender) + " AND friend_id=" + std::to_string(receiver) + ") OR (user_id=" + std::to_string(receiver) + " AND friend_id=" + std::to_string(sender) + ");";
    ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "查询失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }
    res = mysql_store_result(&mysql);
    row = mysql_fetch_row(res);
    int alreadyFriends = std::stoi(row[0]);
    mysql_free_result(res);
    if (alreadyFriends > 0) {
        std::cout << "两人已经是好友" << std::endl;
        return false;
    }

    // 检查是否已经发送过好友请求且未过期
    query = "SELECT COUNT(*) FROM friend_requests WHERE sender=" + std::to_string(sender) + " AND receiver=" + std::to_string(receiver) + ";";
    ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "查询失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }
    res = mysql_store_result(&mysql);
    row = mysql_fetch_row(res);
    int requestExists = std::stoi(row[0]);
    mysql_free_result(res);
    if (requestExists > 0) {
        std::cout << "已经发送过好友请求且未过期" << std::endl;
        return false;
    }

    // 插入好友请求
    query = "INSERT INTO friend_requests (sender, receiver) VALUES (" + std::to_string(sender) + ", " + std::to_string(receiver) + ");";
    ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "查询失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }
    return true;
}


bool acceptFriendRequest(int requestId) {
    // 获取请求的发送者和接收者ID
    std::string query = "SELECT sender, receiver FROM friend_requests WHERE id=" + std::to_string(requestId) + ";";
    int ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "查询失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    MYSQL_ROW row = mysql_fetch_row(res);
    if (row == nullptr) {
        mysql_free_result(res);
        return false;
    }
   std::string senderId = row[0];
   std::string receiverId =row[1];
    mysql_free_result(res);

    // 插入好友关系
    query = "INSERT INTO friends (user_id, friend_id) VALUES (" + senderId + ", " + receiverId + "), (" +receiverId + ", " + senderId + ");";
    ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "插入好友关系失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }

    // 删除好友请求
    query = "DELETE FROM friend_requests WHERE id=" + std::to_string(requestId) + ";";
    ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "删除好友请求失败: " << mysql_error(&mysql) << std::endl;
        return false;
    }

    return true;
}


std::vector<std::tuple<int, int, std::string>> getPendingFriendRequests(int userId) {
    std::vector<std::tuple<int, int, std::string>> requests;
    std::string query = "SELECT fr.id, u.id, u.username FROM friend_requests fr JOIN user u ON fr.sender = u.id WHERE fr.receiver = " + std::to_string(userId) + ";";
    int ret = mysql_query(&mysql, query.c_str());
    if (ret != 0) {
        std::cout << "查询失败: " << mysql_error(&mysql) << std::endl;
        return requests;
    }
    MYSQL_RES* res = mysql_store_result(&mysql);
    MYSQL_ROW row;
    while ((row = mysql_fetch_row(res))) {
        int requestId = std::stoi(row[0]);
        int senderId = std::stoi(row[1]);
        std::string senderName = row[2] ;
        requests.emplace_back(requestId, senderId, senderName);
    }
    mysql_free_result(res);
    return requests;
}
// 其他数据库操作函数可以在这里添加


void handle_user_id(crow::websocket::connection& conn, const crow::json::rvalue& json_data) {
    if (json_data.has("user_id")) {
        long long user_id = json_data["user_id"].i();
        {
            std::lock_guard<std::mutex> lock(connections_mutex);
            connections[user_id] = &conn;
        }
        send_saved_message(user_id);
        std::cout << "User ID " << user_id << " connected" << std::endl;
    }
}

void handle_message(crow::websocket::connection& conn, const crow::json::rvalue& json_data) {
    if (json_data.has("receiver") && json_data.has("message")) {
        long long receiver_id = json_data["receiver"].i();
        long long sender_id = json_data["sender"].i();
        std::string message = json_data["message"].s();
        std::lock_guard<std::mutex> lock(connections_mutex);
        auto it = connections.find(receiver_id);
        if (it != connections.end()) {
            crow::json::wvalue response;
            response["sender"] = sender_id;
            response["type"] = "text";
            response["message"] = message;
            cout << dump(response) << endl;
            it->second->send_text(dump(response));
            std::cout << "Message sent to user ID " << receiver_id << ": " << message << std::endl;
        }
        else {
            std::cerr << "Receiver not connected" << std::endl;
            save_message(sender_id, receiver_id, message);
        }
    }
}


void handle_RTC_id(crow::websocket::connection& conn, const crow::json::rvalue& json_data) {
    if (json_data.has("sender")) {
        long long user_id = json_data["sender"].i();
        {
            std::lock_guard<std::mutex> lock(RTC_connections_mutex);
            RTC_connections[user_id] = &conn;
        }
        std::cout << "User ID " << user_id << " connected" << std::endl;
    }
}

void handle_video_call(crow::websocket::connection& conn, const crow::json::rvalue& json_data) {
    long long receiver_id = json_data["receiver"].i();
    std::string type = json_data["type"].s();

    if (type == "video_call") {
        long long sender_id = json_data["sender"].i();
        std::lock_guard<std::mutex> guard(connections_mutex);
        auto it = connections.find(receiver_id);
        if (it != connections.end()) {
            crow::json::wvalue response;
            response["type"] = "video_call";
            response["sender"] = sender_id;
            cout << dump(response) << endl;
            it->second->send_text(dump(response));
            std::cout << "Vedio call sent to user ID " << receiver_id << std::endl;

            // Start a timer for 30 seconds
            std::thread([receiver_id, sender_id] {
                std::this_thread::sleep_for(std::chrono::seconds(30));
                std::lock_guard<std::mutex> guard(RTC_connections_mutex);
                auto it = RTC_connections.find(receiver_id);
                if (it == RTC_connections.end()) {
                    auto it1 = RTC_connections.find(sender_id);
                    if (it1 != RTC_connections.end()) {
                        crow::json::wvalue response;
                        response["type"] = "timeout";
                        it1->second->send_text(dump(response));
                        std::cerr << "Call request to user ID " << receiver_id << " timed out" << std::endl;
                    }
                }
                }).detach();
        }
        else {
            crow::json::wvalue response;
            response["type"] = "leave";
            conn.send_text(dump(response));
            std::cerr << "Receiver not connected" << std::endl;
        }
    }
    else if (type == "video_call_back") {
        std::lock_guard<std::mutex> guard(RTC_connections_mutex);
        auto it = RTC_connections.find(receiver_id);
        if (it != RTC_connections.end()) {
            crow::json::wvalue response;
            response["type"] = json_data["result"].s();
            it->second->send_text(dump(response));
            std::cout << "Vedio call  back sent to user ID " << receiver_id << std::endl;
        }
    }
}

void handle_webrtc_signaling(const crow::json::rvalue& json_data) {
    std::string type = json_data["type"].s();
    long long receiver_id = json_data["receiver"].i();
    std::lock_guard<std::mutex> guard(RTC_connections_mutex);
    if (type == "offer" || type == "answer") {
        // 转发 SDP 消息
        auto it = RTC_connections.find(receiver_id);
        if (it != RTC_connections.end()) {
                it->second->send_text(dump(json_data));
        }
    }
    else if (type == "candidate") {
        // 转发 ICE 候选者
        auto it = RTC_connections.find(receiver_id);
        if (it != RTC_connections.end()) {
            it->second->send_text(dump(json_data));
        }
    }
}



int main() {
    if (!init_db()) {
        return -1;
    }

    crow::SimpleApp app;

    CROW_ROUTE(app, "/")([]() {
        return "Hello, world!";
        });

    CROW_ROUTE(app, "/login").methods("POST"_method)
        ([](const crow::request& req) 
            {
        auto x = crow::json::load(req.body);
        if (!x)
            return crow::response(400);

        std::string key1 = x["account"].s();
        std::string key2 = x["password"].s();

        // 处理接收到的数据
        std::cout << "Received key1: " << key1 << ", key2: " << key2 << std::endl;

        crow::json::wvalue response;
        bool is_login = login(key1,key2);
        std::cout << is_login  << std::endl;
        response["is_login"] = is_login;

        if (is_login) {
            user_status[x["account"].i()] = 1;
        }

        return crow::response(200,response);
        });


    //注册,无头像选择
    CROW_ROUTE(app, "/register").methods("POST"_method)
        ([](const crow::request&req) {
            crow::json::wvalue response;
            auto x = crow::json::load(req.body);
            if (!x)
                return crow::response(400);
            std::string username = x["username"].s();
            std::string password = x["password"].s();
            if (registerUser(username,password,response)) {
                return crow::response(200, response);
            }
             else {
                return crow::response(500, response);
              }
         });


    CROW_ROUTE(app, "/upload_avatar").methods("POST"_method)
        ([](const crow::request&req) {
        auto x = crow::json::load(req.body);
        if (!x)
            return crow::response(400);
        long long user_id = x["user_id"].i();
        if (!user_id) {
            return crow::response(400, "User ID is required");
        }

        std::string avatar = x["avatar"].s();
        if (avatar.empty()) {
            return crow::response(400, "Avatar data is required");
        }

        try {
            update_avatar(user_id, avatar);
            return crow::response(200, "Avatar uploaded successfully");
        } catch (const std::exception& e) {
        return crow::response(500, std::string("Error: ") + e.what());
          }
        });

    //获取头像
    CROW_ROUTE(app, "/get_avatar").methods("POST"_method)
        ([](const crow::request& req) {
        auto x = crow::json::load(req.body);
        if (!x)
            return crow::response(400);
        long long user_id = x["user_id"].i();
        if (!user_id) {
            return crow::response(400, "User ID is required");
        }
        std::string res = get_avatar(user_id);
        return crow::response(200, res);
         });


    //好友列表
    CROW_ROUTE(app, "/friends_list").methods("GET"_method)
        ([](const crow::request& req) 
            {
                auto userIdStr = req.url_params.get("user_id");
                if (!userIdStr) {
                    return crow::response(400, "Missing user_id parameter");
                }
                long long user_id = std::stoi(userIdStr);

            // 获取好友列表
            crow::json::wvalue friends_list = get_friends_list(user_id);

            return crow::response(200, friends_list);
            });


    CROW_ROUTE(app, "/update_status").methods("POST"_method)
        ([](const crow::request& req) {
        auto x = crow::json::load(req.body);
        if (!x)
            return crow::response(400);
        long long user_id = x["user_id"].i();
        int status_code = x["status_code"].i();
    
        update_user_status(user_id, status_code);
        return  crow::response(200);
         });


    CROW_ROUTE(app, "/send_friend_request").methods("POST"_method)
        ([](const crow::request&req) {
            auto x = crow::json::load(req.body);
            if (!x)
                return crow::response(400);

            long long sender =std::stoi( x["sender"].s());
            long long receiver =std::stoi(x["receiver"].s());

            // 处理接收到的数据
            std::cout << "Received sender: " << sender << ", receiver: " << receiver << std::endl;

            crow::json::wvalue response;
            bool is_request_sent = sendFriendRequest(sender, receiver);
            std::cout << is_request_sent << std::endl;
            response["is_sent"] = is_request_sent;

            return crow::response(200, response);
            });


    CROW_ROUTE(app, "/pending_friend_requests").methods("GET"_method)
        ([](const crow::request&req) {
        // 从查询参数中获取 user_id
            auto userIdStr = req.url_params.get("user_id");
            if (!userIdStr) {
                 return crow::response(400, "Missing user_id parameter");
            }
            long long userId = std::stoi(userIdStr);
            // 获取待确认的好友请求列表
            auto requests = getPendingFriendRequests(userId);

            crow::json::wvalue response;
            int i = 0;
            for (const auto& request : requests) {
                response["requests"][i]["request_id"] = std::get<0>(request);
                response["requests"][i]["sender"] = std::get<1>(request);
                response["requests"][i]["senderName"] = std::get<2>(request);
                i++;
            }

            return crow::response(200, response);
            });


    CROW_ROUTE(app, "/accept_friend_request").methods("POST"_method)
        ([](const crow::request&req) {
            auto x = crow::json::load(req.body);
            if (!x)
                return crow::response(400);

            int requestId = x["request_id"].i();

            // 处理接收到的数据
            std::cout << "Received request ID: " << requestId << std::endl;

            crow::json::wvalue response;
            bool is_request_accepted = acceptFriendRequest(requestId);
            std::cout << is_request_accepted << std::endl;
            response["is_request_accepted"] = is_request_accepted;

            return crow::response(200, response);
            });


    CROW_ROUTE(app, "/send_message").methods("POST"_method)
        ([](const crow::request& req) {
        auto x = crow::json::load(req.body);
        if (!x)
            return crow::response(400);

        long long sender = x["sender"].i();
        long long receiver = x["receiver"].i();
        string message = x["message"].s();
        

        // 处理接收到的数据
        std::cout << "Received message from " << sender << " to " << receiver << ": " << message << std::endl;

        // 查找接收者的连接
        std::lock_guard<std::mutex> guard(connections_mutex);
        auto it = connections.find(receiver);
        if (it != connections.end()) {
            // 发送消息给接收者
            it->second->send_text(message);
            return crow::response(200, "Message sent");
        }
        else {
            return crow::response(404, "Receiver not connected");
        }
            });

    //ws连接
    CROW_ROUTE(app, "/ws")
        .websocket()
        .onopen([&](crow::websocket::connection& conn) {
        std::cout << "WebSocket connection opened" << std::endl;
            })
        .onclose([&](crow::websocket::connection& conn, const std::string& reason) {
                std::lock_guard<std::mutex> lock(connections_mutex);
                for (auto it = connections.begin(); it != connections.end(); ++it) {
                    if (it->second == &conn) {
                        update_user_status(it->first, 0);
                        connections.erase(it);
                        break;
                    }
                }
                std::cout << "WebSocket connection closed: " << reason << std::endl;
            })
        .onmessage([&](crow::websocket::connection& conn, const std::string& data, bool is_binary) {
                std::cout << "Received message: " << data << std::endl;
                auto json_data = crow::json::load(data);
                if (!json_data) {
                    std::cerr << "Failed to parse JSON" << std::endl;
                }
                if (json_data.has("type")) {
                    std::string type = json_data["type"].s();
                    if (type == "initial") {
                        handle_user_id(conn, json_data);
                    }
                    else if (type == "message") {
                        handle_message(conn, json_data);
                    }
                    else if (type == "video_call") {
                        cout << type << endl;
                        handle_video_call(conn, json_data);        
                    }
                    else if (type == "video_call_back") {
                        handle_video_call(conn, json_data);
                    }
                }
              });


      CROW_ROUTE(app, "/ws_RTC")
                .websocket()
                .onopen([&](crow::websocket::connection& conn) {
                    std::cout << "RTC_WebSocket connection opened" << std::endl;
                  })
                .onclose([&](crow::websocket::connection& conn, const std::string& reason) {
                      std::lock_guard<std::mutex> lock(RTC_connections_mutex);
                      for (auto it =RTC_connections.begin(); it != RTC_connections.end(); ++it) {
                          if (it->second == &conn) {
                              RTC_connections.erase(it);
                              break;
                          }
                      }
                        std::cout << "RTC_WebSocket connection closed: " << reason << std::endl;
                    })
                .onmessage([&](crow::websocket::connection& conn, const std::string& data, bool is_binary) {
                        std::cout << "Received message: " << data << std::endl;
                        auto json_data = crow::json::load(data);
                        if (!json_data) {
                            std::cerr << "Failed to parse JSON" << std::endl;
                        }
                        if (json_data.has("type")) {
                            std::string type = json_data["type"].s();
                            if (type == "initial") {
                                handle_RTC_id(conn, json_data);
                            }
                            //else if (type == "veido_call") {
                           //     handle_video_call(conn, json_data);
                            //}
                            else if (type == "offer" || type == "answer" || type == "candidate") {
                                // 处理 WebRTC 信令消息
                                handle_webrtc_signaling(json_data);
                            }
                        }
                 });

    app.port(18080).multithreaded().run();

  
    close_db();
    return 0;
   
}