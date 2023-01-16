#!/home/ubuntu/modrankbot/venv/bin/python3

import logging, sys, os, requests, json, time

import praw

from writedb import recordVoteInDB
from myCreds import *

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def sendTgMessage(message):
    url = f'https://api.telegram.org/bot{tgBotToken}/sendMessage' # ripl shipping spam bot this is 
    payload = {'chat_id':myTgID, 'text': f"""{message}"""}
    requests.post(url,json=payload)

def checkIfParentReallyIsModOfTHATSub(commentObj, parentAuthorObj):
    """
    Returns str of subs modded by parent, if indeed parent was mod of that sub.
    Else, returns False. Also returns False if parent was AutoMod
    """
    if parentAuthorObj.name == "AutoModerator":
        return False
    subWhereCommentWasMade = commentObj.subreddit
    subsModdedByParent = parentAuthorObj.moderated()
    if subWhereCommentWasMade in subsModdedByParent:
        subsModdedByParent = [subName.display_name for subName in subsModdedByParent]
        return ' '.join(subsModdedByParent)
    return False

def checkTheComment(respData: dict, comment:str, author:str, adj:str, positiveVote:bool):
    commentTBCompared = comment.lower().strip(" .!,")
    if commentTBCompared == f'{adj} mod' or commentTBCompared == f'the {adj} mod':
        # check if comment was prevsly handled, as pushshift will naturally send dupes
        commentID = respData['id']
        with open('prevCommIDs.txt', encoding='utf8') as f:
            prevCommIDs = f.read()
        if commentID in prevCommIDs:
            return

        commentObj = REDDIT_OBJ.comment(commentID)
        subreddit = respData['subreddit_name_prefixed']
        parentCommentObj = commentObj.parent()
        commentURL = f"https://www.reddit.com/{respData['permalink']}"
        myLogger.debug(f"{author}\n{comment}\n{subreddit}\n{commentURL}\n{parentCommentObj.author} is parent\n")
        parentAuthorObj = parentCommentObj.author
        subsModdedByParent = checkIfParentReallyIsModOfTHATSub(commentObj, parentAuthorObj)
        if subsModdedByParent:
            myLogger.info("recording db")
            recordVoteInDB(parentAuthorObj.name, positiveVote, subsModdedByParent)
            try:
                commentObj.reply(f"Thanks for voting on {parentAuthorObj.name}.\n\n*On a quest to find the best mods on Reddit.*")
                sendTgMessage("Mod Rank Bot commented, check it out.")
                myLogger.info("Commented succyly")
            except praw.exceptions.RedditAPIException:
                myLogger.warning("Reddit didn't allow to comment, probly coz last comment was swa. Anyway recording vote & carring on...")
        else:
            myLogger.warning(f"False comment. Parent wasn't a mod of sub where comment was made.")
        
        # record handled comment, Pushshift will naturally keep sending dupes
        with open('prevCommIDs.txt', 'a', encoding='utf8') as f:
            f.write(f"{commentID} ")

# configure logging settings
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    myLogger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception # this helps to log all uncaught exceptions
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s-%(levelname)s- %(message)s',
                    handlers=[logging.FileHandler(f"log{os.path.basename(__file__)[:-3]}.txt"), logging.StreamHandler()])
myLogger = logging.getLogger('myLogger')
myLogger.setLevel(logging.DEBUG)

REDDIT_OBJ = praw.Reddit(client_id=rdtClntIDs[0],client_secret=rdtClntSecs[0],user_agent=rdtUsrnms[0], username=rdtUsrnms[0],password=rdtPswds[0])

GOOD_ADJS = ['good', 'great', 'greatest', 'best', 'awesome', 'amazing', 'nice', 'excellent', 'superb']
BAD_ADJS = ['bad', 'worst']

# preparing URL to ping on Pushshift. If term is phrase then wrap in quotes. OR can be indicated with Pipe symbol
thenewAdjs = [f'"{x}' for x in GOOD_ADJS+BAD_ADJS]
searchTerm = '%20mod"|'.join(thenewAdjs)+'%20mod"'
finalURL = f"https://api.pushshift.io/reddit/search/comment/?q={searchTerm}&limit=100"

try:
    r = requests.get(finalURL, timeout=30) # timeout is in secs
except Exception as e:
    myLogger.error(e)
    myLogger.error("Pushshift API gave error, quitting.")
    quit()

respJson = r.json()
for respData in respJson['data']:            
    author = respData['author']
    postID = respData['link_id'][3:]
    comment = respData['body']
    commentID = respData['id']
    for adj in GOOD_ADJS:
        checkTheComment(respData, comment, author, adj, positiveVote=True)
    for adj in BAD_ADJS:
        checkTheComment(respData, comment, author, adj, positiveVote=False)

myLogger.info("Script ran succyly.")