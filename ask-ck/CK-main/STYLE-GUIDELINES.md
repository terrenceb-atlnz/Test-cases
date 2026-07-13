# Design System - Style Guidelines

Extracted and adapted from the Design Guidelines Showcase.

## Design Philosophy

Operational dashboard aesthetic inspired by Linear, Vercel, and Grafana. Five core principles govern all design decisions. 
       
         
           01 
           Clarity over decoration 
           No ornamental gradients, shadows, or animations. Every element earns its place. 
         
         
           02 
           Density with breathing room 
           Efficient layout without sacrificing readability. Information-dense but never cramped. 
         
         
           03 
           Dark and light as equals 
           Both themes are first-class. Design and test in both. Toggle above to verify. 
         
         
           04 
           Predictable interactions 
           Hover states and cursors on all interactive elements. No surprises. 
         
         
           05 
           Accessible by default 
           WCAG 2.1 AA contrast, semantic HTML, keyboard navigation. Not an afterthought.

## Design Tokens (CSS Custom Properties)

See `design-tokens.css` for the complete set (light + dark themes).

Key examples:
- `--accent-primary`
- `--bg-primary` (light/dark)
- `--font-sans`

## Components & Patterns

### Design Philosophy

Operational dashboard aesthetic inspired by Linear, Vercel, and Grafana. Five core principles govern all design decisions. 
       
         
           01 
           Clarity over decoration 
           No ornamental gradients, shadows, or animations. Every element earns its place. 
         
         
           02 
           Density with breathing room 
           Efficient layout without sacr

### Color System

All colors are defined as CSS custom properties. Raw hex values are never used in components. Toggle dark/light mode to see both palettes. 

       
         Backgrounds 
         
               bg-primary  Main content   
               bg-secondary  Cards, panels   
               bg-tertiary  Inset areas   
               bg-sidebar  Sidebar nav   
               bg-elevated  Modals, dropdowns

### Typography

Inter for UI text, JetBrains Mono for code and identifiers. Maximum weight is font-semibold (600). Maximum size is 20px. 

       
         Type Scale 
         
           
             
               Page Title 
               20px / 600 
             
             Equipment Tracking Dashboard 
           
           
             
               Page Description 
               14px / 400 
   

### Spacing &amp; Border Radius

Spacing Scale 
            4px    p-1 — icon gaps  
            6px    p-1.5 — badge padding  
            8px    p-2 — compact elements  
            12px    p-3 — table cells  
            16px    p-4 — card body  
            24px    p-6 — section spacing  
            32px    p-8 — major sections  
         

         
           Border Radius 
           
             
                
      

### Buttons

Four variants. Every button has cursor-pointer and a visible hover state. One primary per section. Destructive actions require confirmation. 

       
         Variants 
         
           
                  
            Create Ticket
           
           
                    
            Export
           
           
                  
            Settings
           
           
           

### Table

Rows are clickable with hover states. IDs use monospace. Header cells are uppercase with tracking. Sortable columns show an indicator. 

       
         
           
             
               Ticket ID          
               Title 
               Priority          
               Status 
               Assignee 
               Updated          
             
           
           
         

### Badges / Status Pills

Each status has a paired text color and muted background. Status is conveyed by more than color alone — always include text labels. 

       
         All Status Variants 
         
           Critical 
           High 
           Medium 
           Low 
           Success 
         
       

       
         In Context 
         
           
                    
            Failed
           
   

### Filter Pills / Tabs

Segmented control pattern. Container uses bg-tertiary, active pill uses bg-elevated with shadow. 

       
         Tab Group 
         
           All Tickets 
           Open 
           In Progress 
           Closed 
         
       

       
         Secondary Example 
         
           7 Days 
           30 Days 
           90 Days 
           All Time

### Form Inputs

Label always above input, never floating. Standard height 36px, compact 32px. Focus ring uses accent-primary. 

       
         
           Standard Inputs 

           
             Ticket Title 
             
           

           
             Priority 
             
               Select priority... 
               Critical 
               High 
               Medium 
               Low 
  

### Cards

bg-secondary background with border. Shadow in light mode only. Clickable cards have a hover border change. 

       
         
           Active Work Orders 
           Equipment maintenance and repair tasks currently in progress. 
           127 
           +12 from last week 
         
         
           Overdue Inspections 
           Scheduled inspections that have passed their due date. 
 

### Sidebar Navigation

Three nav item states: default, hover (simulated), and active. Section labels are uppercase with tracking. 

       
         Main Menu 

         
                
          Dashboard
           default 
         

         
                
          Work Orders
           hover 
         

         
                    
          Equipment
           active 
         

         
               

### Modal &amp; Dropdown

Dialog / Modal 
           bg-elevated with border and shadow-lg. Overlay uses --overlay token. 
           Open Modal 
         

         
           Dropdown Menu 
           bg-elevated, border, shadow-md. Items have hover and cursor-pointer. 
           
             
              Actions
                  
             
             
               
                    
                Edit

### Tooltips

Mandatory for icon-only buttons. 300ms delay, 2-4 word content. bg-elevated with border. 

       
         
           
                      
           
           Refresh data 
         
         
           
                
           
           Filter results 
         
         
           
                    
           
           Download CSV 
         
         
           
         

### Loading States

Skeleton loaders for initial loads. Never use full-page blocking spinners. Skeletons match the shape of the content they replace. 

       
         
           Skeleton Text Lines 
           
              
              
              
             
                
             
           
         

         
           Skeleton Card 
           
             
                
              

### Empty State

Centered layout with large icon, brief message, and call-to-action button. 

       
         
                    
           No work orders found 
           There are no work orders matching your current filters. Create a new one to get started. 
           
                  
            Create Work Order

### Interaction States

Focus Ring (Tab to these buttons) 
           
             Tab to me 
             And me 
             Me too 
           
           Uses focus-visible — no ring on mouse click, visible on keyboard Tab. 
         

         
           Cursor Rules 
           
             cursor-pointer 
             not-allowed 
             cursor-text 
             cursor-grab 
           
         
      

### Notification Bell &amp; User Menu

The top-right header area includes a notification bell with unread count badge and a user avatar dropdown. Both are demonstrated live in the page header above — click them to interact. 

       
         
           Notification Bell 
           
            Icon button with a count badge (rounded-full, status-critical background). Clicking opens a panel with notification items. Unread items use a

### Slide-over / Drawer

A panel that slides in from the right edge. Used for detail views, forms, or secondary content without leaving the current page. 

       Open Slide-over 
       Panel slides in from the right with overlay

### Lightbox

Full-screen overlay for previewing images or media. Click the thumbnail to open. 

       
         
           
                    
             Click to preview 
           
         
         
           
                  
             Document.pdf

### Toast Notifications

Transient feedback messages. Appear bottom-right, auto-dismiss after a few seconds. Four variants: success, error, warning, info. 

       
         
                
          Success Toast
         
         
                  
          Error Toast
         
         
                  
          Warning Toast
         
         
                  
          Info Toast

### Command Palette

Quick search and command launcher. Triggered by keyboard shortcut or button. Uses bg-elevated with overlay. 

       
         
                
          Open Command Palette
         
         or press 
         ⌘ 
         K 
       

       
         Search Input with Shortcut Hint 
         
                
           
            ⌘  K

### Breadcrumbs &amp; Pagination

Breadcrumbs 
           
             Dashboard 
             / 
             Equipment 
             / 
             Building C 
             / 
             HVAC Unit 7 
           
           
             
               Work Orders 
               / 
               TKT-4821 
             
           
         
         
           Pagination 
           
             
                  
     

### Content Tabs

Underline-style tabs for switching content panels. Active tab has an accent-primary bottom border. 

       
         
           Details 
           Activity 
           Attachments 
           Comments 
         
         
           
             Work order details would appear here. Equipment:  EQ-00192  
             Assigned to John Doe. Priority:  Critical  
           
         
         

### Toggles, Checkboxes &amp; Radios

Toggle Switches 
           
             
               
                 Email notifications 
                 Receive email for new ticket assignments 
               
                
             
             
               
                 Auto-assign tickets 
                 Distribute new tickets automatically 
               
                
             
             
             

### Avatars

User avatars in three sizes. Stacked avatar groups for showing multiple assignees. 

       
         
           Sizes 
           
             
               MT 
               24px 
             
             
               JC 
               32px 
             
             
               AP 
               40px 
             
           
         
         
           Avatar Group (Stacke

### Alerts / Banners

Inline notification banners for contextual information. Four variants using status color pairings. 

       
         
                  
           
             Scheduled maintenance 
             System will be unavailable Feb 20 from 2:00-4:00 AM UTC. 
           
         
         
                
           
             Export complete 
             Your CSV export has been generated and 

### Progress Bars

Linear progress indicators using status color tokens. 

       
         
           
             Overall completion 
             73% 
           
           
              
           
         
         
           
             Storage used 
             91% 
           
           
              
           
         
         
           
             Upload progress 
             45%

### Activity Timeline

Vertical timeline for activity feeds and audit logs. 

       
         
            
            John Doe  escalated priority to  Critical  
           2 minutes ago 
         
         
            
            J. Chen  added a comment: "Sensor readings confirm calibration drift beyond tolerance." 
           18 minutes ago 
         
         
            
            System  auto-assigned tic

### Floating Pill Navs

Pill-shaped navigation bars, toolbars, step indicators, and action controls. Floating elements use elevated backgrounds with border and shadow to sit above page content. 

       
       
         Floating Horizontal Pill Bar 
         
           
             
                    
              Dashboard
             
             
                    
              Tickets
             
       

### Miscellaneous Elements

Accordion / Collapsible 
           
             
               
                What equipment types are tracked?
                    
               
               
                 HVAC systems, conveyor belts, pressure sensors, access control panels, emergency lighting, and all electrical switchgear across Building A-D. 
               
             
             
               
          

## Usage

- Use CSS variables exclusively for theming.
- Add `.dark` class to switch themes.
- Refer to `design-guidelines-showcase.html` for interactive examples.
