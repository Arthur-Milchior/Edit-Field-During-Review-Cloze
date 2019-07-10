# -*- coding: utf-8 -*-

"""
Anki Add-on: Edit Field During Review

Edit text in a field during review without opening the edit window

Copyright: (c) 2019 Nickolay <kelciour@gmail.com>
"""

from anki.hooks import addHook, wrap
from anki.utils import htmlToTextLine
from aqt.editor import Editor
from aqt.reviewer import Reviewer
from aqt import mw

import unicodedata
import urllib.parse
import sys


def edit(txt, extra, context, field, fullname):
    config = mw.addonManager.getConfig(__name__)
    txt = """<%s contenteditable="true" data-field="%s">%s</%s>""" % (
        config['tag'], field, txt, config['tag'])
    txt += """<script>"""
    txt += """
            if($("[contenteditable=true][data-field='%s'] > .cloze")[0]){
                $("[contenteditable=true][data-field='%s']").focus(function(){
                    pycmd("ankisave!focuson#%s");
                })
                $("[contenteditable=true][data-field='%s']").blur(function(){
                    pycmd("ankisave#" + $(this).data("field") + "#" + $(this).html());
                    pycmd("ankisave!focusoff#%s");
                })
            }
            else{
                $("[contenteditable=true][data-field='%s']").blur(function() {
                    pycmd("ankisave#" + $(this).data("field") + "#" + $(this).html());
                });
            }     
            """ % (field, field, field, field, field, field)
    if config['tag'] == "span":
        txt += """
            $("[contenteditable=true][data-field='%s']").keydown(function(evt) {
                if (evt.keyCode == 8) {
                    evt.stopPropagation();
                }
            });
        """ % field
    txt += """
            $("[contenteditable=true][data-field='%s']").focus(function() {
                pycmd("ankisave!speedfocus#");
            });
        """ % field
    txt += """</script>"""
    return txt


addHook('fmod_edit', edit)


def saveField(note, fld, val):
    if fld == "Tags":
        tagsTxt = unicodedata.normalize("NFC", htmlToTextLine(val))
        txt = mw.col.tags.canonify(mw.col.tags.split(tagsTxt))
        field = note.tags
    else:
        # https://github.com/dae/anki/blob/47eab46f05c8cc169393c785f4c3f49cf1d7cca8/aqt/editor.py#L257-L263
        txt = urllib.parse.unquote(val)
        txt = unicodedata.normalize("NFC", txt)
        txt = Editor.mungeHTML(None, txt)
        txt = txt.replace("\x00", "")
        txt = mw.col.media.escapeImages(txt, unescape=True)
        field = note[fld]
    if field == txt:
        return
    config = mw.addonManager.getConfig(__name__)
    if config['undo']:
        mw.checkpoint("Edit Field")
    if fld == "Tags":
        note.tags = txt
    else:
        note[fld] = txt
    note.flush()


def myLinkHandler(reviewer, url):
    if url.startswith("ankisave#"):
        fld, val = url.replace("ankisave#", "").split("#", 1)
        note = reviewer.card.note()
        saveField(note, fld, val)
        reviewer.card.q(reload=True)
    elif url.startswith("ankisave!speedfocus#"):
        mw.reviewer.bottom.web.eval("""
            clearTimeout(autoAnswerTimeout);
            clearTimeout(autoAlertTimeout);
            clearTimeout(autoAgainTimeout);
        """)
    elif url.startswith("ankisave!focuson#"):
        val = url.replace("ankisave!focuson#", "")
        mw.reviewer.web.eval("""
        $("[contenteditable=true][data-field='%s']").html("%s")
        """ % (val, reviewer.card.note()[val]))
    elif url.startswith("ankisave!focusoff#"):
        if mw.reviewer.state == "question":
            mw.reviewer._showQuestion()
        elif mw.reviewer.state == "answer":
            mw.reviewer._showAnswer()
        else:
            sys.stderr.write("""'Edit field during review' addon:
            You are not supposed to see this message, but if you are seeing this, there was an error.
            It is probably harmless, and probably doesn't require restart.
            Please report this to the developer.
            unexpected state: %s
            """ % mw.reviewer.state)
    else:
        origLinkHandler(reviewer, url)


origLinkHandler = Reviewer._linkHandler
Reviewer._linkHandler = myLinkHandler
