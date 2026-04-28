# Screenshots Needed for Cookie Extraction Guide

The README.md references the following screenshots that should be added to `docs/images/`:

## Required Screenshots

### 1. `devtools-open.png`
**Location in README:** Step 2 - Open Chrome DevTools

**What to capture:**
- Chrome browser with Tokopedia Affiliate Center page open
- DevTools panel opened (F12 pressed)
- Show both the main page and the DevTools panel
- Highlight the F12 key or right-click → Inspect option

**Instructions:**
1. Open Chrome
2. Navigate to https://affiliate-id.tokopedia.com/connection/creator
3. Press F12 to open DevTools
4. Take screenshot showing both page and DevTools
5. Save as `docs/images/devtools-open.png`

---

### 2. `devtools-application-tab.png`
**Location in README:** Step 3 - Navigate to Application Tab

**What to capture:**
- DevTools with Application tab selected
- Left sidebar showing "Cookies" section expanded
- `https://affiliate-id.tokopedia.com` selected under Cookies
- Highlight the Application tab and Cookies section

**Instructions:**
1. In DevTools, click "Application" tab
2. In left sidebar, expand "Cookies"
3. Click on `https://affiliate-id.tokopedia.com`
4. Take screenshot showing the Application tab and sidebar
5. Save as `docs/images/devtools-application-tab.png`

---

### 3. `devtools-cookies-view.png`
**Location in README:** Step 4 - View and Copy Cookies

**What to capture:**
- Full cookies table showing all Tokopedia cookies
- Important cookies visible: `_SID_Tokopedia_`, `DID`, `_UUID_CAS_`, etc.
- Show columns: Name, Value, Domain, Path, HttpOnly, Secure
- Blur/redact actual cookie values for security

**Instructions:**
1. With cookies displayed in Application tab
2. Ensure important cookies are visible in the table
3. Take screenshot of the cookies table
4. **IMPORTANT:** Blur/redact the "Value" column to protect sensitive data
5. Save as `docs/images/devtools-cookies-view.png`

---

## Optional Screenshots

### 4. `cookie-extension-export.png`
**What to capture:**
- EditThisCookie or Cookie-Editor extension popup
- Export button highlighted
- JSON output preview

### 5. `cookies-json-example.png`
**What to capture:**
- Text editor showing `config/cookies.json` file
- Proper JSON format with array of cookie objects
- Values redacted/blurred for security

---

## Screenshot Guidelines

1. **Resolution:** Minimum 1920x1080 for clarity
2. **Format:** PNG (lossless)
3. **Security:** Always blur/redact actual cookie values
4. **Annotations:** Add arrows or highlights to important elements
5. **Consistency:** Use same browser theme/appearance across all screenshots

---

## Creating Screenshots

### Tools Recommended:
- **Windows:** Snipping Tool, Greenshot
- **Mac:** Cmd+Shift+4 (built-in), Skitch
- **Linux:** Flameshot, Shutter
- **Annotation:** Draw.io, Photoshop, GIMP

### Annotation Tips:
- Use red arrows to point to important elements
- Add numbered circles (1, 2, 3) for step sequences
- Use yellow highlights for text that needs attention
- Keep annotations minimal and clear

---

## Placeholder Images

Until real screenshots are created, the README references these images. The documentation is complete and functional without them, but screenshots would significantly improve user experience.

**Priority:** Medium - Documentation is usable without screenshots, but they would help visual learners.

---

## Alternative: Video Tutorial

Consider creating a short video tutorial (2-3 minutes) showing the cookie extraction process:
1. Opening Chrome and logging in
2. Opening DevTools
3. Navigating to Application → Cookies
4. Exporting cookies with extension
5. Saving to `config/cookies.json`
6. Validating with `python validate_cookies.py`

Video could be hosted on YouTube and linked from README.
