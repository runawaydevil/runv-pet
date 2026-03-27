# Future: Social Mail for Gotchi

This document captures a possible future evolution of `gotchi`: turning the pet into a small in-system courier for pubnix communities such as runv.club.

This is a product and architecture note only. It does not imply that the feature already exists.

## Vision

Each Unix user already has an independent pet. A natural next step is to let pets carry short messages between local users on the same host.

The tone should remain playful and terminal-native:

- not a full chat system
- not a web inbox
- not a daemon-based messenger
- a small, charming courier layer on top of the existing pet experience

Example idea:

```bash
gotchi carry "Hello Will, how are you?" --user will
```

When `will` later runs any `gotchi` command, the pet can show a small notification such as:

- `Your pet brought 1 new letter from pmurad.`

## Product Goals

- Keep the experience lightweight and fun
- Preserve Unix user isolation for pet ownership
- Allow short direct messages between local users
- Surface unread mail inside normal `gotchi` usage
- Make the pet feel socially alive without turning the project into a generic messenger

## Non-Goals

At least for the first social MVP, this should not become:

- a real-time chat system
- a daemon or background service
- a global social feed
- a public message board
- a file transfer system
- an attachment platform
- a group messaging product

## UX Positioning

The pet should feel like the courier, but the commands should stay practical.

Good balance:

- commands are explicit and predictable
- output text is flavorful and pet-driven
- notifications are visible but not noisy

Example tone:

- `Nyx carried your letter to will.`
- `King returned with a reply from will.`
- `Your pet is waiting with 2 unread letters.`

## Proposed Commands

These are candidate commands, not final API.

### Sending

```bash
gotchi carry "Hello Will, how are you?" --user will
gotchi carry --user will --message "Meet me in the gopher lounge"
```

Alternative shorter alias if desired later:

```bash
gotchi send "Hello" --user will
```

Recommendation:

- keep `carry` as the pet-flavored primary command
- avoid too many aliases in the MVP

### Inbox

```bash
gotchi mail
gotchi mail unread
gotchi mail sent
```

Purpose:

- list letters
- highlight unread items
- optionally separate inbox and sent history

### Reading

```bash
gotchi mail read 12
```

This should:

- show full message
- mark it as read
- preserve the message for rereading later

### Replying

```bash
gotchi mail reply 12 "Doing well, thanks."
```

This should:

- create a new message to the original sender
- optionally preserve `reply_to`

### Archiving and Deleting

```bash
gotchi mail archive 12
gotchi mail delete 12
```

This gives a simple life cycle without making the inbox messy.

### Notifications only

```bash
gotchi mail notify
gotchi line
```

`gotchi line` can mention unread mail in a short login-friendly sentence.

## Suggested Command Structure

For long-term clarity, a structure like this is probably healthiest:

- `gotchi carry ...`
- `gotchi mail`
- `gotchi mail read ID`
- `gotchi mail reply ID "..."`
- `gotchi mail archive ID`
- `gotchi mail delete ID`

This keeps:

- sending as a pet action
- mailbox actions under one namespace

## Message States

A message should probably move through explicit states.

Recommended states:

- `new`
- `read`
- `archived`
- `deleted`

Optional internal flags:

- `replied`
- `notification_shown`

Suggested semantics:

- `new`: delivered and not opened yet
- `read`: opened at least once
- `archived`: still stored but hidden from default inbox view
- `deleted`: removed from active view, possibly soft-deleted first

## Proposed Message Model

A future message record could contain:

- `id`
- `sender_uid`
- `sender_username`
- `recipient_uid`
- `recipient_username`
- `body`
- `created_at`
- `delivered_at`
- `read_at`
- `archived_at`
- `deleted_at`
- `status`
- `reply_to_id`
- `sender_pet_name` optional
- `recipient_pet_name_snapshot` optional

Important note:

- UID should be the canonical identity
- username should remain metadata only

## Notification Behavior

Notifications should appear when the user runs normal `gotchi` commands, especially:

- `gotchi`
- `gotchi status`
- `gotchi line`
- perhaps `gotchi mail`

Recommendation:

- green for unread/new letters
- yellow for unread older letters or warnings
- dim or gray for already-read reminders

Example lines:

- `Your pet brought 1 new letter from will.`
- `There are 3 unread letters waiting for you.`
- `A reply from pmurad is still in your satchel.`

The message should be short, warm, and easy to ignore if the user is focused on pet care.

## Storage Model

This is the most important architectural question.

Today, pet storage is private per user, which is ideal for isolation. Inter-user mail changes the problem because one user must be able to send something to another without gaining access to that other user's private pet storage.

### What should not happen

Do not store user-to-user mail directly inside another user's private pet database in a way that the sender can write there directly.

Do not rely on:

- writable home directories of other users
- shared files without strong ownership rules
- environment variables for identity

### Recommended separation

Pet data and social mail should be separate systems.

Recommended model:

- pet storage remains private per user
- social mail gets its own local delivery subsystem

This reduces privacy mistakes and keeps the original pet architecture clean.

### Candidate storage designs

#### Option A: Shared spool directory

A system spool such as:

- `/var/spool/gotchi-mail/`

with message files or per-user inbox directories.

Pros:

- Unix-like
- conceptually simple

Cons:

- permissions become tricky fast
- hard to prevent tampering if done carelessly
- concurrency and integrity become more manual

#### Option B: Shared SQLite database for mail only

A separate database just for courier messages, for example:

- `/var/lib/gotchi/mail.db`

Pros:

- easier indexing and querying
- easier unread counters and threading
- easier soft-delete/archive behavior

Cons:

- requires stronger access controls
- needs very careful write authorization design

#### Option C: Minimal privileged delivery helper

A tiny helper responsible only for depositing and reading letters safely.

Pros:

- strongest control boundary
- can enforce ownership cleanly

Cons:

- operationally more complex
- requires careful security review
- larger maintenance burden

## Recommended Architecture Direction

If this feature is implemented, the safest path is likely:

1. Keep pet storage exactly as it is: private and per-user
2. Build a separate mail subsystem
3. Use UID as canonical identity everywhere
4. Add strong validation for sender and recipient resolution
5. Avoid direct writes from one user into another user's private data area

In other words:

- private pet state stays private
- mail becomes a controlled exchange layer

## Identity Rules

These should remain non-negotiable:

- sender identity comes from real UID
- recipient is resolved from real local account database
- `USER`, `LOGNAME`, `HOME` must not define message ownership
- usernames are display metadata, not trust anchors

Likely source of truth for recipient resolution:

- `pwd.getpwnam()`
- `pwd.getpwuid()`

## Delivery Flow

One possible end-to-end flow:

1. User runs `gotchi carry "..." --user will`
2. CLI resolves sender by real UID
3. CLI resolves recipient by local account database
4. Message is written into the mail subsystem with:
   - sender UID
   - recipient UID
   - body
   - timestamps
   - state `new`
5. Recipient later runs any `gotchi` command
6. `gotchi` checks for unread mail count
7. UI prints a short notification
8. Recipient can open the inbox and read/reply/archive/delete

## Read Flow

Example flow:

1. `gotchi mail`
2. list newest messages first
3. unread letters highlighted in green
4. `gotchi mail read 12`
5. message becomes `read`
6. later `gotchi mail archive 12` if desired

## Reply Flow

Example:

1. `gotchi mail read 12`
2. `gotchi mail reply 12 "Doing well, thanks"`
3. creates a fresh outbound letter
4. stores `reply_to_id=12`

Threading can stay minimal in the MVP.

## Deletion Model

Hard delete is easy but risky for UX. Soft delete is usually safer.

Suggested behavior:

- first implementation may use soft delete internally
- UI can treat deleted messages as hidden
- future admin tooling can purge old deleted records

## Limits and Rate Controls

A local pubnix system still needs anti-abuse rules.

Suggested MVP limits:

- max body length, for example 500 to 1000 chars
- no attachments
- no multiline floods beyond a reasonable cap
- per-user send rate limit
- per-target rate limit

Possible safeguards:

- no more than N messages per minute
- no more than N unread letters from the same sender to the same recipient

## Risks

Main risks:

- security boundary mistakes
- spam
- harassment
- privacy confusion
- permission complexity
- corruption under concurrency
- scope creep
- noisy UX
- moderation burden
- retention growth
- social spoofing through display names or pet names
- mismatch with community culture

## Risk Mitigation

### Security boundary mistakes

Risk:

- a sender might gain a path to read, overwrite or delete another user's letters

Mitigation:

- never store cross-user mail directly in another user's private pet database
- use a separate mail subsystem
- bind sender identity to real UID only
- resolve recipients from the real local account database
- isolate write paths behind controlled delivery logic
- require transaction-safe writes and ownership validation

### Spam

Risk:

- one user can flood another with many short letters

Mitigation:

- add per-user and per-recipient rate limits
- cap body size
- cap number of unread letters from one sender to one recipient
- optionally reject sends when recipient inbox pressure is too high
- keep delivery failures clear and explicit

### Harassment

Risk:

- the feature can become a local harassment channel

Mitigation:

- add archive and delete from day one
- plan for block or mute in the first post-MVP step
- make sender identity explicit in the UI
- document community rules for abuse handling
- provide a minimal moderation path for admins if the host policy requires it

### Privacy confusion

Risk:

- users may not understand who can read messages and what is stored

Mitigation:

- document privacy expectations clearly
- distinguish private pet storage from social mail storage
- define retention behavior before launch
- state whether admins can inspect metadata only or content too
- avoid hidden sharing or public-by-default features

### Permission complexity

Risk:

- Unix permissions for cross-user delivery are easy to get wrong

Mitigation:

- keep the mail subsystem separate from user home storage
- prefer a single controlled system location for message storage
- avoid direct writes into another user's home
- use one clear ownership model for the mail backend
- review permissions and failure modes before rollout

### Corruption under concurrency

Risk:

- concurrent sends, reads and state updates can corrupt mail state

Mitigation:

- use transactional storage
- add locking where needed
- define consistent message state transitions
- test concurrent delivery and reading explicitly
- keep writes short and deterministic

### Scope creep

Risk:

- the project stops being a pet game and turns into a general messenger

Mitigation:

- keep the first version intentionally narrow
- no group messaging in the MVP
- no attachments in the MVP
- no real-time sync or daemon
- keep commands and UX centered on the pet courier metaphor

### Noisy UX

Risk:

- notifications may become annoying if shown too often or too loudly

Mitigation:

- keep notifications short
- show unread count, not full message bodies, in the main dashboard
- use color sparingly
- allow reminders to become dim once seen
- keep mailbox review explicit under `gotchi mail`

### Moderation burden

Risk:

- once messages exist, the host may need to respond to abuse complaints

Mitigation:

- decide the moderation stance before launch
- document what metadata exists
- define whether admin intervention is possible and under what policy
- keep the MVP simple enough that abuse handling stays manageable

### Retention growth

Risk:

- mailboxes may grow forever and clutter the host

Mitigation:

- soft-delete first, then purge old deleted messages later
- define retention windows for archived or deleted mail
- cap inbox size if necessary
- expose archive and delete clearly to users

### Social spoofing through display names or pet names

Risk:

- users may try to mislead others through pet names or display text

Mitigation:

- always display the real local sender username in the message header
- treat pet names as flavor only
- keep UID-backed ownership internally
- never let display names define trust

### Mismatch with community culture

Risk:

- some communities may love the feature, others may see it as noise or social pressure

Mitigation:

- keep the feature optional if possible
- make notifications lightweight
- avoid turning it on as a loud default without community buy-in
- launch as a small experiment before treating it as core infrastructure

## Privacy Considerations

This feature changes the privacy model of the project.

Current project:

- each pet is private to one user

Future mail feature:

- introduces intentional user-to-user communication

That means the design should explicitly state:

- what is private
- who can read what
- whether admins can inspect metadata only or full messages
- how long messages are stored

Recommendation:

- default to private direct messages between local users
- document retention clearly
- avoid public mail features in the first version

## Notification Color Semantics

Suggested terminal colors:

- green: unread new mail
- yellow: pending or older unread mail
- dim: already-read reminders
- red: delivery failure or invalid recipient

Colors must remain optional and degrade cleanly to plain text.

## Integration with Existing Gotchi UX

The mailbox should complement the pet, not dominate it.

Good places to integrate:

- top banner in `gotchi`
- small reminder in `gotchi status`
- short sentence in `gotchi line`

Avoid:

- dumping full inbox automatically on every run
- blocking normal pet actions behind message prompts
- noisy notifications on every command forever

## Suggested MVP Scope

A realistic first social MVP could include only:

- send a letter to one local user
- unread notification in main UI
- inbox listing
- read one message
- reply
- archive
- delete
- basic rate limits
- basic color states

This is enough to feel alive without turning into a major messaging product.

## Suggested Post-MVP Ideas

Possible future expansions after the MVP proves stable:

- block or mute sender
- sent mailbox
- conversation view
- per-user courier preferences
- temporary delivery failures with retry messaging
- themed pet delivery text by species
- public event board or town square
- read-only memorial or public post office board

These should not ship in the first social version.

## Operational Considerations

Before implementation, these questions should be answered clearly:

- where does the mail subsystem live on disk?
- who owns it?
- can users inspect only their own messages?
- how are permissions enforced?
- how are concurrent writes handled?
- what retention policy applies?
- what moderation model exists for abuse cases?

## Recommendation Summary

Recommended direction:

- yes, pursue the idea
- keep the pet as the courier metaphor
- keep commands explicit and terminal-friendly
- keep pet storage private and separate
- build social mail as an isolated subsystem
- use UID as canonical identity everywhere
- ship a narrow MVP first

## Example MVP UX

Send:

```bash
gotchi carry "Hello Will, how are you?" --user will
```

Notification later:

- `Your pet brought 1 new letter from pmurad.`

Inbox:

```bash
gotchi mail
gotchi mail read 4
gotchi mail reply 4 "Doing well, thanks."
gotchi mail archive 4
```

## Final Note

This feature has strong potential because it turns `gotchi` into a social part of the host culture rather than only a private toy. The key to doing it well is restraint: keep it small, safe, and charming.
