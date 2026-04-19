# CV Tailoring Improvements

## Problem

The original CV tailoring system was:
1. Converting CVs to Markdown format (losing original formatting)
2. Not preserving the user's CV template/style
3. Creating a completely new document instead of editing the original

**User's Request**: "Use the candidate's same CV template and update it, keep all existing information that doesn't need to be changed"

## Solution

Updated the CV generator to:

### ✅ For DOCX Files (Recommended)
1. **Downloads** the user's original DOCX file from storage
2. **Loads** the document preserving all formatting
3. **Intelligently finds and replaces** specific sections:
   - Professional Summary
   - Skills section
   - (Keeps everything else intact - fonts, colors, layout)
4. **Saves** as a new DOCX file
5. **Original CV** remains untouched

### ✅ For PDF Files
1. Downloads the original PDF
2. Creates a new professional DOCX with tailored content
3. (Note: PDFs can't be easily edited while preserving format)
4. Saves as DOCX

## How It Works

### File: `backend/app/services/cv_generator.py`

#### New Method: `_create_tailored_cv_file()`
```python
async def _create_tailored_cv_file(
    original_cv_data: bytes,  # Original CV file
    original_file_type: str,  # 'pdf' or 'docx'
    tailored_content: Dict,   # AI-generated tailored content
    ...
) -> tuple[str, bytes, str]:  # Returns: (filename, file_bytes, content_type)
```

**For DOCX**:
- Loads the document using `python-docx`
- Calls `_update_docx_content()` to intelligently update sections
- Preserves all formatting (fonts, colors, styles, margins)
- Returns updated DOCX

**For PDF**:
- Creates a new professional DOCX from scratch
- Uses tailored content
- Returns new DOCX

#### New Method: `_update_docx_content()`
```python
def _update_docx_content(doc, tailored_content, cv_data, job):
    """
    Updates DOCX while preserving formatting.

    Finds sections by markers:
    - "Professional Summary" / "Summary" / "Objective" / "Profile"
    - "Skills" / "Technical Skills" / "Core Competencies"

    Replaces content in those sections only.
    Preserves all original formatting.
    """
```

**Smart Section Detection**:
1. Scans document paragraphs
2. Looks for section headers (case-insensitive)
3. Identifies the content paragraph(s) after the header
4. Preserves font name, size, bold, italic
5. Replaces only the text content
6. Leaves everything else untouched

#### New Method: `_replace_text_in_doc()`
```python
def _replace_text_in_doc(doc, markers, new_text, section_name):
    """
    Finds and replaces text in specific sections.

    Process:
    1. Find section header matching any marker
    2. Get next paragraph (the content)
    3. Extract current formatting (font, size, style)
    4. Clear text
    5. Insert new text
    6. Restore original formatting
    """
```

#### Fallback Method: `_create_new_docx()`
```python
async def _create_new_docx(tailored_content, cv_data, job, timestamp):
    """
    Creates a professional DOCX from scratch.

    Used when:
    - Original format is PDF
    - DOCX editing fails
    - Unknown file type

    Creates:
    - Professional header with name and contact
    - Sections: Summary, Skills, Experience, Education
    - Clean formatting with proper spacing
    - Footer note indicating job targeting
    """
```

## Updated Flow

### Before (Old System)
```
1. Get user's CV metadata from database
2. Use parsed content (JSON)
3. Generate AI tailored content
4. Convert to Markdown
5. Save as .md file
6. Original format lost ❌
```

### After (New System)
```
1. Get user's CV metadata from database
2. Download original CV file from storage
3. Generate AI tailored content
4. Edit original DOCX (preserves format) ✅
   OR Create professional DOCX (for PDFs)
5. Save as new DOCX file
6. Original CV untouched ✅
```

## File Structure in Storage

```
cvs/ (bucket)
├── {user_id}/
│   └── cv_abc123.docx                              ← Original CV (NEVER MODIFIED)
└── tailored-cvs/
    └── {user_id}/
        ├── tailored_cv_{job1_id}_20250109_120000.docx  ← Tailored for Job 1
        ├── tailored_cv_{job2_id}_20250109_130000.docx  ← Tailored for Job 2
        └── tailored_cv_{job1_id}_20250110_140000.docx  ← Regenerated for Job 1
```

## What Gets Updated

### ✅ Updated Sections
- **Professional Summary**: Tailored to emphasize skills relevant to the job
- **Skills**: Reordered to highlight most relevant skills first
- **Footer**: Small note added: "Tailored for: [Job Title] at [Company]"

### ❌ NOT Updated (Preserved)
- Personal Information (name, email, phone)
- All formatting (fonts, colors, styles, sizes)
- Document layout and margins
- Work experience entries (kept as-is)
- Education section (kept as-is)
- Projects section (kept as-is)
- Any other sections

## Benefits

### ✅ For Users
1. **Original CV preserved** - never modified
2. **Same look and feel** - keeps their professional template
3. **Only text changes** - formatting stays consistent
4. **Multiple versions** - can generate different tailored CVs for different jobs
5. **Professional output** - DOCX format for easy sharing

### ✅ For AI Matching
1. **Focuses on relevance** - highlights skills matching the job
2. **Reorders content** - puts most relevant info first
3. **Tailors summary** - writes a summary specific to the job
4. **Maintains accuracy** - never fabricates information

## Limitations

### PDF Files
- Cannot edit PDFs while preserving exact formatting
- PDF structure is complex and layout-based
- Solution: Create a new professional DOCX instead
- Future: Could add PDF generation from DOCX

### Complex DOCX Layouts
- Tables, images, charts are preserved but not edited
- Only text in paragraphs is updated
- Very complex templates might need manual adjustment

## Testing

### Test with DOCX
1. Upload a DOCX CV
2. Generate tailored CV for a job
3. Download result
4. Check: Original formatting preserved, text updated

### Test with PDF
1. Upload a PDF CV
2. Generate tailored CV for a job
3. Download result
4. Check: Professional DOCX created with tailored content

## Future Improvements

### Potential Enhancements
1. **PDF Editing**: Use more advanced PDF libraries to edit PDFs directly
2. **Smart Section Detection**: Use AI to identify section headers more accurately
3. **Experience Tailoring**: Update work experience bullets to emphasize relevant achievements
4. **PDF Export**: Convert tailored DOCX back to PDF for final submission
5. **Template Library**: Offer pre-made professional CV templates
6. **Visual Preview**: Show before/after comparison in UI

## Code Changes

### Modified Files
- `backend/app/services/cv_generator.py` - Complete rewrite of CV generation logic

### New Methods Added
- `_create_tailored_cv_file()` - Main method for creating tailored CV files
- `_update_docx_content()` - Updates DOCX content preserving format
- `_replace_text_in_doc()` - Finds and replaces text in sections
- `_create_new_docx()` - Fallback method to create new DOCX

### Dependencies Used
- `python-docx` - For DOCX reading and writing
- `PyPDF2` / `pdfplumber` - For PDF reading (if needed)

## User Experience

### Before
1. Click "Generate Tailored CV"
2. Get a Markdown file
3. Lose all formatting
4. Need to manually reformat ❌

### After
1. Click "Generate Tailored CV"
2. Get a DOCX file with same format as original
3. Only relevant text updated
4. Ready to use ✅

---

**Updated**: 2025-01-09
**Status**: ✅ Complete
**Impact**: Major improvement to CV tailoring UX
