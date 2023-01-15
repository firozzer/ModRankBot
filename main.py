import logging, sys, os

import praw

from writedb import recordVoteInDB
from myCreds import *

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def checkIfParentReallyIsModOfTHATSub(commentObj, theParentAuthorObj):
    """
    Returns "automoderator" string if parent was that.
    Else, returns str of subs modded by parent, delimiter is space
    If parent wasn't the mod of the sub in which comment was made, returns False
    """

    if theParentAuthorObj.name == "AutoModerator":
        return 'AutoModerator'
    subWhereCommentWasMade = commentObj.subreddit
    subsModdedByParent = theParentAuthorObj.moderated()
    if subWhereCommentWasMade in subsModdedByParent:
        subsModdedByParent = [subName.display_name for subName in subsModdedByParent]
        return ' '.join(subsModdedByParent)
    return False

def checkTheComment(commentObj, adj: str, positiveVote: bool):
    commentBody = commentObj.body
    if commentBody.lower().strip(" .!,") == f'{adj} mod':
        myLogger.info(f"https://reddit.com/{commentObj.link_id[3:]}")
        myLogger.info(f"{commentBody} - {commentObj.author}")
        theParentCommentObj = commentObj.parent()
        theParentAuthorObj = theParentCommentObj.author
        myLogger.info(f"The parent is {theParentCommentObj.author}")
        try:
            hi = True
            # commentObj.reply(f"Thank you for voting on {theParentCommentObj.author}")
        except praw.exceptions.RedditAPIException:
            myLogger.warning("Reddit didn't allow to comment, probly coz last comment was swa. Anyway recording vote & carring on...")
        subsModdedByParent = checkIfParentReallyIsModOfTHATSub(commentObj, theParentAuthorObj)
        if subsModdedByParent:
            if subsModdedByParent == 'AutoModerator':
                subsModdedByParent = 'all'
            myLogger.info("recording db")
            recordVoteInDB(theParentAuthorObj.name, positiveVote, subsModdedByParent)
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
    goodAdjectives = ['good', 'great', 'greatest', 'the greatest', 'best', 'the best', 'awesome', 'amazing', 'nice']
    basAdjectives = ['bad', 'worst']
    for adj in goodAdjectives:
        checkTheComment(commentObj, adj, True)
    for adj in basAdjectives:
        checkTheComment(commentObj, adj, False)
