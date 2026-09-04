# Password policy

Twelve **characters**. Not twelve bytes.

A user who types twelve characters has typed twelve characters, whatever
alphabet they are in. The rule as the sign-up page states it, as the help centre
states it, and as the customer understands it, counts what they typed.

⚠ Counting UTF-8 bytes lets an **eight-character** password through as soon as
four of its characters are outside ASCII, because each of those costs two bytes.
That is the whole of the defect and it is worst for exactly the users who are
least likely to be typing ASCII.

🚨 **The answer is not to strip the accents.** A policy measured on what a
password reduces to in ASCII rejects a perfectly good twelve-character Swedish
or Japanese password outright, and it is a worse rule than the one it replaces:
the byte count was too permissive for some users, and an ASCII count is
impossible for them.
