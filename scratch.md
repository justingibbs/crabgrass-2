1. Front line employee opens Crabgrass and logs in
2. Sees homepage with sections for "Contributing to" and "Shared with me". Sees none in Contributing but one in "Shared with me"
3. Clicks to starte a new Idea
4. Idea opens with a 
2. Sees that they have no Ideas that they are contributing on or own. See that some ideas have been shared with them


Review @AI_README.md and files in @context. Then help me implement slice 2 of @implementation-plan-v1.md. Create a 

Review @AI_README.md, all files in @context/ and especially @context/implementation-plan-v1.md. Then help me implement Slice 8. Ask me any questions you may have before writing code. And if you'd like, feel free to create a task list or whatever for this slice under @context/ 


--- Slice 3 - complete but need to test

  To test manually:
  # Terminal 1
  cd backend && rm -f data/crabgrass.duckdb && uv run uvicorn crabgrass.main:app --reload --port 8000

  # Terminal 2
  cd frontend && npx serve . -l 3000

  Then visit http://localhost:3000, create an idea, and explore the workspace!


---

Main screens
- Screen 1: Ideas List (Home): Very similar to what we have in @wireframes.md. But instead of "My Ideas" the section should be "Contributing to". Any new Idea the user creates would fall under "Contributing to". Also include a section for "Objectives"
- Screen 2: New Idea Modal: This is not a modal but rather an empty "creen 3: Idea Workspace (Main View)". It should be more like Claude Projects stacked vertically, with the Kernal (Summary, Challenge, Approach, Coherent Steps) are actual Markdown files in the project under the section "Kernel Files". Under that section is a "Context Files" section where users can upload additional files (same as "Files" in Claude Projects). Above the "Kernel Files" section is a chat window where the user chats with "CoherenceAgent" agent (there is also some functionality to start a new sessioin or pull up an older one - this functionality should be available for all chat windows). At the top of the page is a section for Objective but it is not populated yet and a share/collaborators section/button. At the bottom of the page is a Publish/Archive button.
- Screen 3: Idea Workspace (Main View): This should also mirror Claude Projects more and actually open a new screen where the screen has chat running down the left side and the markdown file open in a Canvas on the right side. Users can focus on just this section of their work with the chat window communicating with the corresponding agent. At the top there can be some version control functionality and at the bottom a Cancel/Save button. Also the chat allows users to manage chat sessions. There should be a completeness indicator as well (this will be determined by the corresponding agent)NOTE: This will also be the same layout for the "Create Objective" screen.
- Editing a Context File: This should be the same as Screen 3: Idea Workspace but LLM Chat should talk with ContextAgent.
- Objective Dropdown (Expanded): This looks good. Just understand that most likely the "CoherenceAgent" will the one who suggests to the user to pick one and be specific of which one is more related. 
- Objective Workspace: Same as creen 3: Idea Workspace but instead of the "Kernel Files" there is just one for "Objective.md". 


Idea sharing status:
- Shared with me: can add comments but can't edit
- Contributor: can add comments and edit
- Owner: can add comments, edit, add/remove collaborators, transfer ownership