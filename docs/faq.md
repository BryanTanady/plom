<!--
__copyright__ = "Copyright (C) 2019-2020 Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
 -->

Frequently Asked Questions
==========================

Common questions and tips 'n tricks that may not appear elsewhere in the
documentaiton.


Plom Client software
--------------------

### Some windows/dialogs are awkward to resize on Gnome Desktop

You could try disabling "Attach Modal Dialogs" in the "Gnome Tweaks" app.


### I don't like ____ about the UI, why don't you do ____?

We are not experts at UI design: please do send patches or merge requests
to help improve Plom.


Identifying
-----------

### How does the auto-identifier work?

Machine learning trained on the MNIST handwritten digit dataset.  A linear
assignment problem solver then matches the results against the class list.
For this reason the class list csv file should not contain large numbers
of additional students that are not in your class.


Test Preparation
----------------

### My QR codes are badly misplaced

This might be a bad interaction with `\scalebox` in LaTeX.
See [this bug](https://gitlab.com/plom/plom/issues/207).


Marking
-------

### Why do you have "+0" and "-0" as possible delta-marks?

Mathematics use "epsilon" to represent small number, often in the context of limits. Some markers like to indicate to students via (say) "-0" that there is a small error in their work but it is too small to reduce their overall mark. Similarly some markers use "+0" to indicate that a small amount of progress has been made, but not enough to be worth a full point. This also give the marker the option of deciding that (say) three "-0" on a question will result in a "-1". One can indicate that by drawing arrows from the "-0"s to a "-1" marker. However if there are only one or two "-0"s then the mark is unchanged. Similarly if the question has (say) three "+0" then the marker might decide that is worth "+1".

### Why don't you just give fractional marks instead?

Because the developers of Plom don't use them. We feel that they tend to over-complicate marking schemes and that it is better to simply make your test out of a larger total rather than mess about with "1/2"s or "1/3"s. This also makes things more consistent when a large team is trying to mark using the same scheme / rubric. We admit that this is forcing our own ideas about marking onto others, however, after supervising the marking of many tests and exams, we feel that this is the right way to go (the absence of fractional marks, not the forcing people to do what we think)

Of course, if an energetic co-developer would like to implement fractional marks, then we won't stop them. 
