#!/home/ubuntu/modrankbot/venv/bin/python3

import logging, sys, os, requests

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

def checkTheComment(respData: dict, adj:str, positiveVote:bool):
    author = respData['author']
    comment = respData['body']
    commentID = respData['id']
    commentTBCompared = comment.lower().strip(" .!,")
    if commentTBCompared == f'{adj} mod' or commentTBCompared == f'the {adj} mod':
        # check if comment was prevsly handled, as pushshift will naturally send dupes. If it was prevsly handled, just return.
        with open('prevCommIDs.txt', encoding='utf8') as f:
            prevCommIDs = f.read()
        if commentID in prevCommIDs:
            return

        commentObj = REDDIT_OBJ.comment(commentID)
        subreddit = respData['subreddit_name_prefixed'] # result will be string like 'r/dubai' (r/ included)
        parentCommentObj = commentObj.parent()
        commentURL = f"https://www.reddit.com/{respData['permalink']}"
        myLogger.debug(f"{author}\n{comment}\n{subreddit}\n{commentURL}\n{parentCommentObj.author} is parent")
        parentAuthorObj = parentCommentObj.author
        subsModdedByParent = checkIfParentReallyIsModOfTHATSub(commentObj, parentAuthorObj)
        if subsModdedByParent:
            myLogger.info("recording db")
            recordVoteInDB(parentAuthorObj.name, positiveVote, subsModdedByParent)
            # check if prevsly commented in post, if yes then dont comment again to reduce spam. Vote will get recorded still.                
            with open('postIDsWhereIPrvslyComntd.txt', encoding='utf8') as f:
                postIDsWhereIPrvslyComntd = f.read()
            postID = respData['link_id'][3:]
            if postID not in postIDsWhereIPrvslyComntd:
                try:
                    commentObj.reply(f"Thanks for voting on **{parentAuthorObj.name}**. Reply '!OptOut' to stop replying.\n\n*Curating Reddit's best mods.*")
                    myLogger.info("Commented succyly")
                    sendTgMessage(f"Mod Rank Bot commented: {commentURL}")
                    # record post ID where commented, so as not to coment again in that post to reduce spam
                    with open('postIDsWhereIPrvslyComntd.txt', 'a', encoding='utf8') as f:
                        f.write(f"{postID} ")
                except Exception as e:
                    myLogger.info(f"ModRankBot Couldn't comment publicly. Commenter: {author} , ParentMod: {parentAuthorObj.name}, Sub: {subreddit}. Is this a banned sub? See if error is specific to banned sub. Anyway, sending DM to {author}. Error is: {e}")
                    sendTgMessage(f"ModRankBot Couldn't comment publicly. Commenter: {author} , ParentMod: {parentAuthorObj.name}, Sub: {subreddit}. Is this a banned sub? See if error is specific to banned sub. Anyway, sending DM to {author}. Error is: {e}")
                    try:
                        commentAuthorObj = REDDIT_OBJ.redditor(author)
                        commentAuthorObj.message(subject=f"Thanks for voting on u/{parentAuthorObj.name} in {subreddit}", message=f"[Your vote]({commentURL}) has been successfully recorded. Reply '!OptOut' to stop replying.\n\n*Curating Reddit's best mods.*")
                        sendTgMessage(f"ModRank Bot here,  https://reddit.com/{postID}, DM'd u/{author}.")
                    except Exception as e:
                        myLogger.error(f"Error when trying to DM {author} https://reddit.com/{postID} : {e}")
                        sendTgMessage(f"ModRank Bot failed to DM https://reddit.com/{postID}, DM failed to u/{author}.")
            else:
                myLogger.info(f"Already commented in Post {postID}, so DMing u/{author}.")
                # TODO uncomment below 2 lines the day your bot rank improves, it will send DM to voter that their vote ws recorded. Not posting in post to reduce spam.
                try:
                    commentAuthorObj = REDDIT_OBJ.redditor(author)
                    commentAuthorObj.message(subject=f"Thanks for voting on u/{parentAuthorObj.name} in {subreddit}", message=f"[Your vote]({commentURL}) has been successfully recorded. Reply '!OptOut' to stop replying.\n\n*Curating Reddit's best mods.*")
                    sendTgMessage(f"ModRank Bot already commented in Post https://reddit.com/{postID}, so DM'd u/{author}.")
                except Exception as e:
                    myLogger.error(f"Error when trying to DM {author} https://reddit.com/{postID} : {e}")
                    sendTgMessage(f"ModRank Bot failed to DM https://reddit.com/{postID}, DM failed to u/{author}.")
        else:
            if parentCommentObj.author == 'AutoModerator':
                myLogger.info(f"Skipped recording vote since parent was AutoMod.")
            else:
                myLogger.warning(f"False comment. {parentAuthorObj.name} isn't a mod of {subreddit}, where comment was made.")
        
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

idxOfModRankBotCreds = rdtUsrnms.index('modrankbot')
REDDIT_OBJ = praw.Reddit(client_id=rdtClntIDs[idxOfModRankBotCreds],client_secret=rdtClntSecs[idxOfModRankBotCreds],user_agent=rdtUsrnms[idxOfModRankBotCreds], username=rdtUsrnms[idxOfModRankBotCreds],password=rdtPswds[idxOfModRankBotCreds])

GOOD_ADJS = ['good', 'great', 'greatest', 'best', 'awesome', 'amazing', 'nice', 'excellent', 'superb', "excellente", "excelent", "wonderful", "brave", "super", "incredible", "sweet", "lovely", "bold", "sexy", "gg", 'cool', 'mvp', 'og', 'goat']
BAD_ADJS = ['bad', 'worst', "insensitive", "harsh", "rash", "rude", "senseless", "dictatorial", 'dumb', 'inconsiderate']

# preparing URL to ping on Pushshift. If term is phrase then wrap in quotes. OR can be indicated with Pipe symbol
thenewAdjs = [f'"{x}' for x in set(GOOD_ADJS+BAD_ADJS)] # set is to remove dupes if any
searchTerm = '%20mod"|'.join(thenewAdjs)+'%20mod"'
finalURL = f"https://api.pushshift.io/reddit/search/comment/?q={searchTerm}&limit=100"

try:
    r = requests.get(finalURL, timeout=60) # timeout is in secs
except Exception as e:
    myLogger.error(f"Quitting. Pushshift API gave error: {e}")
    quit()

if r.ok:
    respJson = r.json()
else:
    myLogger.error(f"Received 'not ok' resp from Pushshift. Status code: {r.status_code}, Content: {r.content}")
    quit()

for respData in respJson['data']:            
    for adj in GOOD_ADJS:
        checkTheComment(respData, adj, positiveVote=True)
    for adj in BAD_ADJS:
        checkTheComment(respData, adj, positiveVote=False)

myLogger.info("Script ran succyly.")