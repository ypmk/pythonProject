import os
import zlib
import string
import re


def getText(filename):
    file = open(filename, 'rb')
    text = file.read()
    file.close()
    return zlib.decompress(text)
def parseCommit(text, file_name, commitsNames):
    commit = {}
    decoded = text.decode("utf-8")
    matchName = re.search(r'\n(.+)\n*$', decoded) #regular expressions engine example match of Initial commit
    matchParent = re.search(r'parent (.+)\n', decoded)
    matchTree = re.search(r'tree (.+)\n', decoded)
    if (matchName):
        name = matchName[1] #exampole initial commit (name)
        if (name not in commitsNames):
            commitsNames.append(name)
            if (matchParent):
                commit['parent'] = matchParent[1]
            if (matchTree):
                commit['tree'] = matchTree[1]
            commit['id'] = file_name
            commit['name'] = name
    return commit
def gitType(filePath, path):
    path = os.path.normpath(path)
    gitPath = ".git\objects"
    gitPath = os.path.normpath(gitPath)
    gitPath = os.path.join(path, gitPath, filePath[0:2], filePath[2:])
    return getText(gitPath).split()[0].decode("utf-8")
def parseTree(text, fileName, path):
    tree = {}
    tree["type"] = "tree"
    tree["name"] = fileName
    files = []
    byte = text.find(b'\x00')
    text = text[byte + 1:]

    files = []

    while len(text): # Разбираем файл дерева на отдельные файлы и складываем в tree
        byte = text.find(b'\x00')
        lineName = text[0:byte].decode("utf-8").split() #example ['100644', ".gitignore"]
        text = text[byte + 1:]
        filePath = text[0:20]
        files.append({
            "type": gitType(filePath.hex(), path), #exampole blob
            "mode": lineName[0], #example 100644
            "name": lineName[1], #example ,dz5.iml, .gitignore
            "filePath": filePath.hex() #example 26d...ef5
        })
        text = text[20:]
        tree["files"] = files
    return tree
def orderCommits(commits):
    orderedCommits = []

    for cm in commits:
        if (not cm.get('parent')):
            orderedCommits.append(cm)
            break

    # print(orderedCommits)

    for i in range(len(commits) - 1):
        for cm in commits:
            # print(cm)
            if (cm.get('parent') and orderedCommits[-1]['name'] == cm['parent']):
                orderedCommits.append(cm)
                break

    return orderedCommits

# SUMMARY
# Берем базу коммитов и базу деревьев, которые спарсили до этого и объндинятем, приписывая нужные деревья нужным коммитам
# Ориентируемся на имена деревьев и имена дерева справшенного из коммита, затем пробегаясь по всем деревьям вытаскиваем узлы
# Принадлежащие кажддому из деревьев, таким образом выстраивается нужная иерарзия, где каждое дерево приналдежит либо коммиту либо дереву
# (А, ну еще файлы приписываем нужным узлам)
def getNodes(commits, trees):
    nodes = []
    newCommits = []

    for cm in commits:
        newCommit = {}
        if (cm.get('parent')):
            newCommit['parent'] = cm['parent']
        newCommit['name'] = cm['name']
        newCommit['nodes'] = []
        for tree in trees:
            if (cm['tree'] == tree['name']):
                for node in tree['files']: #Передаем новому коммиту все по наследству, затем перебирая узды в дереве, которое принаджежит этому коммиту изем деревья(деревья в деревьях, да)  и запихиваем их в nodes
                    if (node['type'] == 'tree' and node not in nodes):
                        newCommit['nodes'].append({'type': 'dir', 'name': node['name'], 'nodes': []})
                        # nodes.append(node)
                        for tempTree in trees: # Изем потомков для каждого из деревьев(теперь уже директорий), тем самым выстраивая нужную иерархию (ищеи в сформерованной базе васех деревьев (trees))
                            if (node['filePath'] == tempTree['name']):
                                for tempNode in tempTree['files']:
                                    if (tempNode['type'] == 'tree' and tempNode not in nodes):
                                        newCommit['nodes'][-1]['nodes'].append(
                                            {'type': 'dir', 'name': tempNode['name'], 'nodes': []})
                                        # nodes.append(tempNode)
                                        for tempTree2 in trees: # добавляем в иехархию не деревья(директории), а файлы
                                            if (tempNode['filePath'] == tempTree2['name']):
                                                for tempNode2 in tempTree2['files']:
                                                    if (tempNode2['type'] == 'blob' and tempNode2 not in nodes):
                                                        newCommit['nodes'][-1]['nodes'][-1]['nodes'].append(
                                                            {'type': 'file', 'name': tempNode2['name']})
                                                        # nodes.append(tempNode2)
                                for tempNode in tempTree['files']:
                                    if (tempNode['type'] == 'blob' and tempNode not in nodes):
                                        newCommit['nodes'][-1]['nodes'].append(
                                            {'type': 'file', 'name': tempNode['name']})
                                        # nodes.append(tempNode)
                for node in tree['files']:
                    if (node['type'] == 'blob' and node not in nodes):
                        newCommit['nodes'].append({'type': 'file', 'name': node['name']})
                        # nodes.append(node)
        newCommits.append(newCommit)

    return newCommits


def getCommits(path):
    gitPath = ".git\objects"
    gitPath = os.path.join(os.path.normpath(path), os.path.normpath(gitPath)) # Конкатенируем пути
    gitPath = os.walk(gitPath)

    commits = []
    commitsNames = []
    trees = []

    for object in gitPath: # example: ('C:\\Users\\morning\\PycharmProjects\\dz5\\.git\\objects\\10', [], ['5ce2da2d6447d11dfe32bfb846c3d5b199fc99'])
        if (len(object[2]) == 1):
            filePath = os.path.join(object[0], object[2][0]) #example 'C:\\Users\\morning\\PycharmProjects\\dz5\\.git\\objects\\10\\5ce2da2d6447d11dfe32bfb846c3d5b199fc99'
            fileName = object[0][-2] + object[0][-1] + object[2][0] #examople '105ce2da2d6447d11dfe32bfb846c3d5b199fc99'
            text = getText(filePath)
            type = text.split()[0].decode("utf-8") #Сплитуем по пробелу и смотрим первое слово
            if type == "commit":
                commit = parseCommit(text, fileName, commitsNames)
                if (commit.get('name')):
                    commits.append(commit)
            elif type == "tree":
                tree = parseTree(text, fileName, path)
                trees.append(tree)

    for cm in commits: # Устанавливаем человеческое имя родителя для коммита (К примеру, initial commit для второго комиита)
        if (cm.get('parent')):
            for commit in commits:
                if (cm['parent'] == commit['id']):
                    cm['parent'] = commit['name']
                    break
    for cm in commits:
        cm.pop('id')

    # print(commits)

    commits = orderCommits(commits) # Складываем коммиты в нужном порядке
    # print(trees)
    nodes = getNodes(commits, trees) #Широкое описание в summary
    return nodes

# SUMMARY
# Формируем итоговую строку исходя из информации, какой коммит обрабатываем, какого типа узел принаджедащий коммиту
# В зависимости оттиформации придаем цвет и печатаем зависимости
# Главным образом отслеживание информации просзодит через counter, указывающий на объект
# Который сейчас обрабатывается (при начале установки зависимостей сбрасывается в ноль)
def getGraph(commits=[]):
    graph = "digraph Commits {\n"

    cmColor = "#ff92c2"
    dirColor = "#595758"
    fileColor = "#FFC8FB"

    counter = 0
    for commit in commits:
        graph += f'  {counter}[label="Commit: {commit["name"]}", color="{cmColor}"]\n'
        counter += 1
        for node in commit['nodes']:
            if (node['type'] == 'file'):
                graph += f'  {counter}[label="File: {node["name"]}", color="{fileColor}"]\n'
                counter += 1
            elif (node['type'] == 'dir'):
                graph += f'  {counter}[label="Directory: {node["name"]}", color="{dirColor}"]\n'
                counter += 1

                for n in node['nodes']:
                    if (n['type'] == 'file'):
                        graph += f'  {counter}[label="File: {n["name"]}", color="{fileColor}"]\n'
                        counter += 1
                    elif (n['type'] == 'dir'):
                        graph += f'  {counter}[label="Directory: {n["name"]}", color="{dirColor}"]\n'
                        counter += 1

                        for k in n['nodes']:
                            if (k['type'] == 'file'):
                                graph += f'  {counter}[label="File: {k["name"]}", color="{fileColor}"]\n'
                                counter += 1
                            elif (k['type'] == 'dir'):
                                graph += f'  {counter}[label="Directory: {k["name"]}", color="{dirColor}"]\n'
                                counter += 1
    counter = 0
    commitCounter = 0
    dirCounter = 0
    prevDirCounter = 0
    for commit in commits:
        if (commit.get('parent')):
            graph += f'  {commitCounter} -> {counter}\n'
        commitCounter = counter # с каким коммитом работаем (при имении предка указываем)
        counter += 1
        for node in commit['nodes']:
            if (node['type'] == 'file'):
                graph += f'  {commitCounter} -> {counter}\n'
                counter += 1
            elif (node['type'] == 'dir'):
                graph += f'  {commitCounter} -> {counter}\n'
                prevDirCounter = counter
                counter += 1
                for n in node['nodes']:
                    if (n['type'] == 'file'):
                        graph += f'  {prevDirCounter} -> {counter}\n'
                        counter += 1
                    elif (n['type'] == 'dir'):
                        graph += f'  {prevDirCounter} -> {counter}\n'
                        dirCounter = counter
                        counter += 1
                        for k in n['nodes']:
                            graph += f'  {dirCounter} -> {counter}\n'
                            counter += 1
    graph += "}"

    return graph


if __name__ == "__main__":
    path = os.getcwd() # Нынешняя директория

    commits = getCommits(path)
    graph = getGraph(commits)
    print(graph)