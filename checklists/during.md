# during.md

Purpose: questions an agent asks itself before each individual operation
on the DAW session (not once per whole task — once per action).

- 今から変えるオブジェクトは何か (What object am I about to change?)
- それは上書きか追加か (Is this an overwrite or an addition?)
- deny.txt に当たるか (Does this action match a rule in `policy/deny.txt`? Yes/No)

If the action matches `policy/deny.txt`, do not perform it. Instead, add
it to the "Denied actions" line of the after-run report
(`checklists/after.md`) and continue with the rest of the task if
possible.
