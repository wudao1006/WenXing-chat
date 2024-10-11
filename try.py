# with open('test.txt', 'r', encoding='utf-8') as file:
#     long_text = file.read()
#
# # 使用Python的str.split函数将文本分割成段落
# paragraphs = long_text.split('\n')
#
# # 使用str.strip函数去除每个段落的前后空白
# paragraphs = [para.strip() for para in paragraphs]
#
# # 过滤掉空的段落
# sentences = [para for para in paragraphs if para]
# with open('test_result.txt', 'w', encoding='utf-8') as file:
#     for sentence in sentences:
#         file.write(sentence+'\n')
import sys

sys.path.append(r"C:\Users\86130\PycharmProjects\pythonProject\venv\Lib\site-packages\co_caculate.cp39-win_amd64.pyd")
import co_caculate
import os

print(co_caculate.setImage("t1"))
