import logging, sys, os, requests

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

def checkTheComment(commentObj, adj: str, positiveVote: bool):
    commentBody = commentObj.body
    commentBodyTBCompared = commentBody.lower().strip(" .!,")
    if commentBodyTBCompared == f'{adj} mod' or commentBodyTBCompared == f'the {adj} mod':
        myLogger.info(f"https://reddit.com/{commentObj.link_id[3:]}")
        myLogger.info(f"{commentBody} - {commentObj.author}")
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

for commentObj in reddit.subreddit('all').stream.comments(skip_existing=True):
    goodAdjectives = ['good', 'great', 'greatest', 'best', 'awesome', 'amazing', 'nice', 'excellent', 'superb']
    badAdjectives = ['bad', 'worst']
    for adj in goodAdjectives:
        checkTheComment(commentObj, adj, True)
    for adj in badAdjectives:
        checkTheComment(commentObj, adj, False)
