import logging, sys, os, requests, pyperclip, json, time

import praw

from writedb import recordVoteInDB
from myCreds import *

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def sendTgMessage(message):
    url = f'https://api.telegram.org/bot{tgBotToken}/sendMessage' # ripl shipping spam bot this is 
    payload = {'chat_id':myTgID, 'text': f"""{message}"""}
    requests.post(url,json=payload)

def checkIfParentReallyIsModOfTHATSub(commentObj, theParentAuthorObj):
    """
    Returns str of subs modded by parent, if indeed parent was mod of that sub.
    Else, returns False. Also returns False if parent was AutoMod
    """
    if theParentAuthorObj.name == "AutoModerator":
        return False
    subWhereCommentWasMade = commentObj.subreddit
    subsModdedByParent = theParentAuthorObj.moderated()
    if subWhereCommentWasMade in subsModdedByParent:
        subsModdedByParent = [subName.display_name for subName in subsModdedByParent]
        return ' '.join(subsModdedByParent)
    return False

def checkTheComment(comment:str, author:str, adj: str, positiveVote: bool):
    commentTBCompared = comment.lower().strip(" .!,")
    if commentTBCompared == f'{adj} mod' or commentTBCompared == f'the {adj} mod':
        myLogger.info(f"{comment} - {author}")
        return 
        theParentCommentObj = commentObj.parent()
        theParentAuthorObj = theParentCommentObj.author
        myLogger.info(f"The parent is {theParentCommentObj.author}")
        subsModdedByParent = checkIfParentReallyIsModOfTHATSub(commentObj, theParentAuthorObj)
        if subsModdedByParent:
            myLogger.info("recording db")
            recordVoteInDB(theParentAuthorObj.name, positiveVote, subsModdedByParent)
            try:
                commentObj.reply(f"Thanks for voting on {theParentAuthorObj.name}.\n\n*On a quest to find the best mods on Reddit.*")
                sendTgMessage("Mod Rank Bot commented, check it out.")
                myLogger.info("Commented succyly")
            except praw.exceptions.RedditAPIException:
                myLogger.warning("Reddit didn't allow to comment, probly coz last comment was swa. Anyway recording vote & carring on...")
        else:
            myLogger.warning(f"False comment. Parent wasn't a mod of sub where comment was made.")

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

reddit = praw.Reddit(client_id=rdtClntIDs[0],client_secret=rdtClntSecs[0],user_agent=rdtUsrnms[0], username=rdtUsrnms[0],password=rdtPswds[0])
myLogger.info("Script started.")

goodAdjectives = ['good', 'great', 'greatest', 'best', 'awesome', 'amazing', 'nice', 'excellent', 'superb']
badAdjectives = ['bad', 'worst']

# preparing URL to ping on Pushshift. If term is phrase then wrap in quotes. OR can be indicated with Pipe symbol
thenewAdjs = [f'"{x}' for x in goodAdjectives+badAdjectives]
searchTerm = '%20mod"|'.join(thenewAdjs)+'%20mod"'
finalURL = f"https://api.pushshift.io/reddit/search/comment/?q={searchTerm}&limit=100"

while True:
    r = requests.get(finalURL, timeout=30) # timeout is in secs
    respJson = r.json()
    for respData in respJson['data']:            
        author = respData['author']
        comment = respData['body']
        for adj in goodAdjectives:
            checkTheComment(comment, author, adj, positiveVote=True)
        for adj in badAdjectives:
            checkTheComment(comment, author, adj, positiveVote=False)
    time.sleep(5)