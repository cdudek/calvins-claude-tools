---
type: owner-words
updated: 2026-10-29
---

# The owner's words

Every request the owner has made about HeyDiff, the team service, verbatim, dated. Quote from this file; never cite a request by number. Grouped by day, in the order asked. The source is the chat or dialog of that day.

The Mac app's own requests are in `heydiff-desktop/docs/ux/owner-words.md`. Decisions the owner answered on the spec's defaults are in `changes/2026-10-27-online-release-1/spec/owner-decisions.md`, and each lasting decision has its own file in `docs/designs/`.

## 2026-10-27

> "What I would like to do is to have an app where a team can work together to comment, similar to how we do this at the moment by pressing 1 and adding annotations, but on different DOM elements."
>
> — 2026-10-27, owner, chat

> "In a nutshell it's an online service where you, as a team, can work together and provide feedback on the actual design and you can provide this feedback to the AI via MCP."
>
> — 2026-10-27, owner, chat

> "You would provide feedback, you would have comments, you would request changes, and then the AI would mark it as, "Hey I implemented these changes." Then someone, whether it's a developer or another human, would go through these changes afterward and confirm these changes were properly done."
>
> — 2026-10-27, owner, chat

> "I still would want people to draw there, to comment."
>
> — 2026-10-27, owner, chat

> "I suppose when on localhost it needs to also recognise which folder this is and potentially which branch or work tree or whatever."
>
> — 2026-10-27, owner, chat

> "It should be a Chrome extension for sure."
>
> — 2026-10-27, owner, chat

> "login wise, I want email magiclink, github and google workspace / google. I want to be able to link accounts across different sign in methods."
>
> — 2026-10-27, owner, chat

> "we will use resend as first email client, but implement it as factory or strategy pattern."
>
> — 2026-10-27, owner, chat

> "we use heroui, Initially I want minimal styling from the base except colors, border radius, and general theming, we should still define it where necessary."
>
> — 2026-10-27, owner, chat

> "i dont want inline or adhoc design but clear resuable tokens, a glossary, next i18n implemented from the get go with language english as default and only inital language."
>
> — 2026-10-27, owner, chat

> "I want a simple and effective ui, calm, productive."
>
> — 2026-10-27, owner, chat

> "it should also be able to ask questions and support decisions in the discussion of the feedback. this needs to go beyond just discussing it in a comment bubble treat but voting and discussing for alternative solutions e.g. mockups?"
>
> — 2026-10-27, owner, chat

> "it should capture context e.g. main-content-area and point to a specific module or functionality that needs redesign or adjustments within that context.."
>
> — 2026-10-27, owner, chat

> "Vote and comment on versions. the agent doesnt live in the app but it's joins as copilot of the engineer or who ever drives the feedback."
>
> — 2026-10-27, owner, chat

> "we should at least capture this, so when a developer get asked to address feedback, the AI knows which version this was and where to find it."
>
> — 2026-10-27, owner, chat

> "we also need to include staging environments, production environment e.g. example.com => prod, example.ninja => staging"
>
> — 2026-10-27, owner, chat

> "we also need an operator area btw. so we have public for marketing, landing pages and blog, app, admin"
>
> — 2026-10-27, owner, chat

> "assume on phones there will be mainly answering to comments or stuff." · "and approve stuff" · "critical stuff"
>
> — 2026-10-27, owner, dialog

> "cloud setup, use local development first, only on release 2 we are going to think about deployment. until then, all locally but gcs. we will use terraform yes."
>
> — 2026-10-27, owner, chat

> "resend => for now send to terminal. I will provide templates later and key for resend later."
>
> — 2026-10-27, owner, chat

> "Chrome web store dev acccount, you can still develop it locally first without an account."
>
> — 2026-10-27, owner, chat

> "Make sure the chrome extension thing locates components and files, etc." · dialog: "next, react, vue, nuxt"
>
> — 2026-10-27, owner, chat

> "planning should be done initially and certain things then be done in parallel. e.g. mcp, mac localhost bridge, landing/waitlist, webapp."
>
> — 2026-10-27, owner, dialog

> "I want you to use tools like impeccable and frontend-designer. to make the experience look great. as well as the ux-pattern skill and heroui components and patterns with wrappers."
>
> — 2026-10-27, owner, dialog

> "ideally in parallel also using codex sol 6.1 and sonnet 5.5 models."
>
> — 2026-10-27, owner, chat

> "Two-way sync" (what the Mac app does online in the first release)
>
> — 2026-10-27, owner, dialog

> "Left sidebar" · "this way, by page navigation and so one would be a subnavigation later down the road"
>
> — 2026-10-27, owner, dialog

> "Strict" (prompt injection from feedback text in the MCP)
>
> — 2026-10-27, owner, dialog

> "I want you to use use laws of ux, interaction guidelines, adhere to our design guidelines, use ui max plugins, sitemap properly planned, etc."
>
> — 2026-10-27, owner, plannotator

> "important copy and marketing language always hopes and dreams level never, feature level communication"
>
> — 2026-10-27, owner, chat

> "Comment, draw, vote" (what guests may do in release 1; no Approve or Request changes)
>
> — 2026-10-27, owner, dialog

## 2026-10-28

> "Agent" (the label word for the coding assistant acting through MCP; "Copilot" becomes an alias)
>
> — 2026-10-28, owner, dialog

> "he changes the state of the specific comment/comments" (how a fix made by hand, without an agent, moves on)
>
> — 2026-10-28, owner, dialog

> "Claim and ask need write" (an agent needs a write scope to claim a feedback or ask a question)
>
> — 2026-10-28, owner, dialog

> "Browser with loopback" (how the Mac app signs in to HeyDiff; no device code)
>
> — 2026-10-28, owner, dialog

> "the current design looks very grey in grey. also there is no dark mode version. can we research modern calm saas design, also colour palette wise I am open"
>
> — 2026-10-28, owner, chat

> "A. Clear Sky" (the colour direction for HeyDiff, light and dark, from `spec/research/calm-saas-colour.md`)
>
> — 2026-10-28, owner, dialog

> "for SNAPMARK, we want not a monorepo but to have everything separate" · "You should have a separate repository" · "also rename local folder and make sure we also have a snapmark-chrome repo and folder"
>
> — 2026-10-28, owner, chat

> "and one for snapmark-terraform"
>
> — 2026-10-28, owner, chat

> "Move it to snapmark-web" (the plan of this release moves from the desktop repo to the web repo, now `heydiff-desktop` and `heydiff-web`)
>
> — 2026-10-28, owner, dialog

> "I know currently have the diamond for references but we should have a comment symbol with avatar badge from whom the feedback is."
>
> — 2026-10-28, owner, chat

> "feedback should be simple so why is there a title. should be as simple as vercels feedsback tool or google drive. generally I dont like the direction."
>
> — 2026-10-28, owner, chat

> "i'm in the browser, reviewing localhost:3000, giving feedback to the current version, it's committed or not, local or preview or staging or in production, I go through the app and give feedback. I may see other peoples comments but I can also deactivate other peoples feedback to be visible. each comment sits for itself. I wouldnt even initially make it session based but version / commit based."
>
> — 2026-10-28, owner, chat

> "then in the application you can go through the different comments including screenshots and annotations. and make there decisions. people can upload mockups, figma links, text options, in a dialog and what not and come to a decision. then the ai may says it fixed it and then it indicates revision #1 or what not, not sure here, and users can feedback on that again or say this is resolved."
>
> — 2026-10-28, owner, chat

> "that is the rough journey. did I forget anything? should we extend it? anyways I want screens through the whole journey. including theme, ideally with darkmode as default."
>
> — 2026-10-28, owner, chat

> "Okay, all very ready. What I'm missing, however, is the option to draw, similar to how this is in the desktop app, so that I would want to draw stuff."
>
> — 2026-10-28, owner, chat

> "I also want to be able to select elements and see the DOM elements." · "The selection, how you select stuff, how you select elements, is not visible, also as part of the feedback."
>
> — 2026-10-28, owner, chat

> "it's not only pointing with text on an element and with a screenshot or an image from the section, but also knows the exact part of the code, including the file and so on, and what component is currently there. It would be great if you can update it towards this."
>
> — 2026-10-28, owner, chat

> "By the way I like the logo of the extension, at least the one from placing a comment. This looks quite nice."
>
> — 2026-10-28, owner, chat

> "as part of the extension and the panel, potentially be able to change the screen size and the resolution." · "Maybe you should just have common devices like MacBook Air 13-inch, MacBook Pro 14-inch, 16-inch."
>
> — 2026-10-28, owner, chat

> "I mean this logo. can we properly design it?" (the rounded-square "S" mark, not the comment icon; corrects the reading of A49)
>
> — 2026-10-28, owner, chat, with a crop of the extension icon

> "I think it still would make sense to have the concept of a session: if something was feedback in one session, it also would be able to be shared with others, like, "Hey here's my feedback session," whether it's sharing it with AI or sharing it with other developers. I mean technically they would also just see the current comments on this version but I think it would help to share a specific session and have the concept of a session"
>
> — 2026-10-28, owner, chat

> "logo looks awful, so I will create something outside" (the owner supplies the logo; screens keep a placeholder until then)
>
> — 2026-10-28, owner, chat

> "drawings, augmentation, drawing, squares, and moving elements would also be nice. We would be able to drag and drop elements in the DOM, moving things around, including left align, right align, and so on. What's basically still missing is just drawing, being able to draw"
>
> — 2026-10-28, owner, chat

> "ok that looks nice, I dont like the filter icon though."
>
> — 2026-10-28, owner, chat

> "also can you also create a first draft of the landing page / for marketing?"
>
> — 2026-10-28, owner, chat

> "15 · Select an element there should be a 15.2 Is it possible to select multiple elements, e.g., by holding Shift or something?"
>
> — 2026-10-28, owner, chat

> "landing page looks like shit. implement a basic placeholder one in Release 1."
>
> — 2026-10-28, owner, chat

> "I like the journey. Please save them, including all the screenshots, and consider this as approved and we can continue to the technical design."
>
> — 2026-10-28, owner, chat

> "I just wonder whether we can have similar button types as you would have in Material UI, also having a nice hover animation, ideally with ripple. I like ripple. I would love to have the same ripple effect as Material UI, the Vue.com framework, without importing the framework per se, but maybe rebuilding it."
>
> — 2026-10-28, owner, chat

> "Generally I want to have smooth very smooth and subtle motion."
>
> — 2026-10-28, owner, chat

> "The journey is approved (A59); move on to the technical plan and design."
>
> — 2026-10-28, owner, chat

> "can you create secure and hardned docker nodejs images based on ~/projects/*infra also take a similar approach to the terraform setup, however no kubernetes but cloud run for now. also use similar CI pipelines without the ship, show, ask. yet we dont have argocd so we need to accomodate for that. make sure you using the latest version from remote."
>
> — 2026-10-28, owner, chat

> "ok so the domain is heydiff.com this is the idea" … "change all the repo names and folder names accordingly including all documentation"
>
> — 2026-10-28, owner, chat

> "we have the url and everything. I bought the domain."
>
> — 2026-10-28, owner, chat

> "initally no warming up, just pay as we go for cloud run"
>
> — 2026-10-28, owner, chat

> "One brand, new ids" (the Mac app is renamed HeyDiff too, with new ids)
>
> — 2026-10-28, owner, dialog

> "New project heydiff" (a new GCP project for HeyDiff)
>
> — 2026-10-28, owner, dialog

> "Inside online-release-1 (the Mac app's new ids `com.heydiff.mac`, the `heydiff-updates` feed, the data migration and the hand-over release ship as a milestone of this change: Beads `snap-70l.1`, size L, feature)"
>
> — 2026-10-28, owner, dialog

> "Any reply reopens" (any reply, member or guest, sets a Revised comment back to Open)
>
> — 2026-10-28, owner, dialog

> "C starts a new comment" (Esc keeps the draft as a draft pin; C always starts a new comment)
>
> — 2026-10-28, owner, dialog

> "Cloud Run from release 1" (staging and production on Cloud Run from milestone 1; local development stays)
>
> — 2026-10-28, owner, dialog

> "let it run in germany ideally frankfurt"
>
> — 2026-10-28, owner, chat

> "GCS and Bigquery should be EU, instances preferably frankfurt"
>
> — 2026-10-28, owner, chat

> "well fucking write it down. I don't care it doesnt exist" (the residency rule covers buckets and datasets that do not exist yet)
>
> — 2026-10-28, owner, chat

> "I want a CI and a CD on merge to Master" (a merge to `main` runs CI, then deploys staging, then production; no manual promotion)
>
> — 2026-10-28, owner, chat

> "One /goal for everything" (one `/goal` runs all milestones, chosen over one goal per milestone)
>
> — 2026-10-28, owner, dialog

> "(decision) heydiff.com is hosted in AWS Route53 and stays there; the owner enters the DNS records by hand from a Terraform output"
>
> — 2026-10-28, owner, dialog

> "why fucking firebase? I dont want to use firebase"
>
> — 2026-10-28, owner, chat

> "why do I need a loadbalancer" (on fronting Cloud Run with a global load balancer, because domain mapping is missing in Frankfurt)
>
> — 2026-10-28, owner, chat

> "ok do belgium then" (after learning Cloud Run domain mapping is offered in no German region: compute moves to europe-west1, domain mapping in Preview accepted)
>
> — 2026-10-28, owner, chat

> "(decision) one development database per developer on the Cloud SQL instance, `dev-calvin-dudek` and `dev-sophie-philipp`, made by `make dev-db` and Terraform"
>
> — 2026-10-28, owner, dialog

## 2026-10-29

> "mention the doc with the imags and mockups, that we should validate against it"
>
> — 2026-10-29, owner, plan gate (plannotator)

## States and feedback (2026-10-29)

> "do we have rulesets on loading e.g. when and what e.g. when using skeleton, progress bar, or spinner? if not we should define this. this is essential for good ux. same for toast messages, different states including empty, as well as error handling. I want this defined and always taken care of."
>
> — 2026-10-29, owner, chat

## States and feedback, review of the first draft (2026-10-29)

The owner's annotation on `interaction-guidelines.md`, binding. The revised section tags the rules it settled "owner, 2026-10-29".

> I’d resolve these before making it binding:
>
> 1. **A new toast must not remove someone’s recovery option.**  
> TOA-7 explicitly removes the previous Undo when another toast appears. Reopen covers Resolve, but the inventory also includes Delete Comment and Discard. Copying a link could therefore remove the only way to recover discarded work. Keep recovery available independently of the toast. Also reconcile replacement with “Problem stays until closed.” A timed action without an equivalent untimed alternative needs particular care under [WCAG’s timing guidance](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html).
>
> 2. **A failed reply must not overwrite the next draft.**  
> In the example, Ben’s failed reply returns to the composer after a timeout. What if he has already started another reply? WEB-6’s approach—keeping the failed item with Try Again—is safer. Preserve each submission separately; restoring one to the composer must preserve anything already there.
>
> 3. **Rewrite the loading table so its branches do not overlap.**  
> “Pick the first row that fits” currently selects:
> - Known-layout skeletons before the existing-content refresh case.
> - Busy buttons before optimistic updates.
> - Earlier cases before the “over 10 seconds” case.
>
> Separate **operation type** from **elapsed time**, and explicitly exempt immediate button feedback from the 400 ms delay. Similarly, EMP-8’s “loading, error, empty, content” order needs an exception for refreshing existing content: a failed refresh should retain the readable content and show its error alongside it.
>
> 4. **Define what a timeout actually means.**  
> LOD-11 promises an error at 30 seconds, while ERR-4 allows three retries and ERR-5 gives a request 30 seconds. Specify one overall waiting budget. For writes, distinguish *confirmed failure* from *no confirmation received*: the server may have saved a reply even though the response never arrived. The same-key retry rule is useful, but needs reconciliation of late responses and a rule for edited retry payloads.
>
> 5. **Give navigation and shortcuts explicit precedence.**  
> Three conflicts need a direct answer:
> - WEB-2 restores the focused row on Back; LOD-13 moves focus to the page heading.
> - EDT-5 uses ⌘Z for drawings; TOA-9 uses it for the visible toast.
> - WEB-3 treats Esc as a history pop, but a directly opened detail page may have no list behind it.
>
> Define which interaction owns the key and focus. For a directly opened detail page, provide a known list destination.
>
> 6. **Strengthen the accessibility checks.**  
> Checking at 100% and 150% leaves gaps. Add 200% text resizing and reflow at 320 CSS pixels, with applicable exceptions for genuinely two-dimensional content. Those are the relevant [WCAG resize and reflow requirements](https://www.w3.org/TR/WCAG22/#reflow). Also, LOD-8’s blanket 60% opacity can undermine the contrast promised by ACC-3. Keep readable text at compliant contrast and indicate refresh separately.
>
> 7. **Separate rule status from proof of compliance.**  
> “Proposed,” “approved,” “awaiting confirmation,” and “in force until the owner answers” leave implementers unsure what governs. Give each rule a clear approval status and state which rules take precedence.
>
> Likewise, an E2E test title proves that a state is registered, not that its behavior works. Require assertions for preservation, recovery, focus and transitions. Resolve the smaller inconsistency between allowing an ancestor error boundary and requiring an error file in every route.
>
> I’d add four worked examples to make these decisions concrete: **two quick destructive actions; a reply failing while another is being written; a refresh failing with content already visible; and Esc from a directly opened detail page.** Each should specify what remains visible, what survives, where focus goes, and how recovery works.
>
> — 2026-10-29, owner, review (plannotator)
