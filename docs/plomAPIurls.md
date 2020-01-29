# URLs used for the PLOM API

## TODOs
* build a proper API document which shows inputs and return values etc.

## Misc information
* get "/Version" - return server+API versions as test string
* get "/info/shortName" - return the shortname of the test (from spec)
* get "/info/general" - return a list (name, #tests, #pages, #groups, #versions)

## Authentication + misc Admin tasks
* put "/users/{user}" - verify user/password + return auth-token
* delete "/users/{user}" - close user-session + revoke auth-token
* delete "/authorisation" - removes authorisation token from a user
* put "/admin/reloadUsers" - force server to reload user list
* put "/admin/reloadScans" - force server to reload scans

## Identifier
* get "/ID/progress" - return [#done, #total]
* get "/ID/tasks/available" - return [next available task] or 204-code (if none)
* get "/ID/classlist" - return classlist file
* get "/ID/predictions" - return prediction-list file
* get "/ID/tasks/complete" - return list of tasks completed by that user
* get "/ID/images/{tgv}" - return the image-file for that TGV
* patch "/ID/tasks/{task}" - claim task (if still available) - return imagefile
* put "/ID/tasks/{task}" - update the ID/Name of the task (ie test)
* delete "/ID/tasks/{task}" - unclaim task - ie tell server that user did not finish that task - go back on todo list

## Totaller
* get "/TOT/maxMark" - return max-total-mark for test
* get "/TOT/progress" - return [#done, #total]
* get "/TOT/tasks/complete" - return list of tasks completed by that user
* get "/TOT/tasks/available" - return [next available task] or 204-code (if none)
* get "/TOT/images/{tgv}" - return imagefile of that tgv
* patch "/TOT/tasks/{task}" - claim task (if still available) - return imagefile
* put "/TOT/tasks/{task}" - update the mark of the task (ie test)
* delete "/TOT/tasks/{task}" - unclaim task

## Marker
* get "/MK/maxMark" - return max-mark for the page-group
* get "/MK/progress" - return [#done, #total]
* get "/MK/tasks/complete" - return list of tasks completed by that user
* get "/MK/tasks/available" - return next available task
* get "/MK/latex" - take latex-fragment, process and return png
* get "/MK/images/{tgv}" - return original imagefile of that tgv plus the annotated version plus the plom-file
* get "/MK/originalImage/{test}/{group}" - return (original, unannotated) imagefile
* get "/MK/whole/{number}" - return group-images of entire paper (except id-page)
* patch "/MK/tags/{tgv}" - save user-tags of that tgv
* put "/MK/tasks/{tgv}" - send back marked-image, plom-file, comments, mark etc.
* patch "/MK/tasks/{task}" - claim the task (if still available) - return imagefile
* delete "/MK/tasks/{task}" - unclaim the task.


## List of routes from grep of image_server.py
Placed a checkmark next to each if appears in lists above.

* get("/Version") ✓
* delete("/users/{user}") ✓
* put("/users/{user}") ✓
* put("/admin/reloadUsers") ✓
* put("/admin/reloadScans") ✓
* get("/info/shortName") ✓
* get("/info/general") ✓
* get("/ID/progress") ✓
* get("/ID/tasks/available") ✓
* get("/ID/classlist") ✓
* get("/ID/predictions") ✓
* get("/ID/tasks/complete") ✓
* get("/ID/images/{tgv}") ✓
* patch("/ID/tasks/{task}") ✓
* put("/ID/tasks/{task}") ✓
* delete("/ID/tasks/{task}") ✓
* get("/TOT/maxMark") ✓
* get("/TOT/tasks/complete") ✓
* get("/TOT/progress") ✓
* get("/TOT/tasks/available") ✓
* patch("/TOT/tasks/{task}") ✓
* delete("/TOT/tasks/{task}") ✓
* get("/TOT/images/{tgv}") ✓
* put("/TOT/tasks/{task}") ✓
* get("/MK/maxMark") ✓
* delete("/MK/tasks/{task}") ✓
* get("/MK/tasks/complete") ✓
* get("/MK/progress") ✓
* get("/MK/tasks/available") ✓
* patch("/MK/tasks/{task}") ✓
* get("/MK/latex") ✓
* get("/MK/images/{tgv}") ✓
* get("/MK/originalImage/{test}/{group}") ✓
* put("/MK/tasks/{tgv}") ✓
* patch("/MK/tags/{tgv}") ✓
* get("/MK/whole/{number}") ✓

<!-- # Table of functions etc - shows need for harmonisation
|method|url|messenger|server|DB|
|------|----|----|----|----|
| get | "/Version" |.|.|.|
| put | "/users/{user}"| requestAndSaveToken | giveUserToken | giveUserToken |
| delete | "/users/{user}" | closeUser | closeUser | closeUser |
| get |"/ID/progress" | IDprogressCount | IDprogressCount | IDprogressCount|
| get |"/ID/tasks/available"| IDaskNextTask | IDaskNextTask | IDaskNextTask |
| get |"/ID/classlist"| IDrequestClasslist | IDrequestClasslist | . |
| get |"/ID/predictions" | IDrequestPredictions | IDrequestPredictions | . |
| get |"/ID/tasks/complete" | IDrequestDoneTasks | IDrequestDoneTasks | IDrequestDoneTasks |
| get |"/ID/images/{tgv}" | IDrequestImage | IDrequestImage | IDrequestImage |
| patch |"/ID/tasks/{task}"| IDclaimThisTask | IDclaimThisTask | IDclaimThisTask |
| put |"/ID/tasks/{task}" | IDreturnIDdTask | IDreturnIDdTask | IDreturnIDdTask |
| delete |"/ID/tasks/{task}" | IDdidNotFinishTask | IDdidNotFinishTask | IDdidntFinish | -->
