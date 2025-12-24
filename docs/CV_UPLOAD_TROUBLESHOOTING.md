# CV Upload Troubleshooting

## Common 400 Bad Request Errors

### Error: "Invalid file type"

**Possible Causes:**
1. File extension not recognized (e.g., `.PDF` instead of `.pdf`)
2. File has no extension
3. File type not in allowed list (only `.pdf` and `.docx` are allowed)

**Solutions:**
- Ensure file has `.pdf` or `.docx` extension (case-insensitive)
- Check file is actually a PDF or DOCX (not renamed text file)
- Verify filename is not empty

**Check Backend Logs:**
```
Uploading file: filename.pdf, extension: .pdf, content_type: application/pdf
```

### Error: "File too large"

**Cause:** File exceeds 10MB limit

**Solution:** Compress or reduce file size

### Error: "File is empty"

**Cause:** Uploaded file has 0 bytes

**Solution:** Ensure file is not corrupted and has content

### Error: "File must have a filename"

**Cause:** File object has no filename attribute

**Solution:** Ensure frontend sends file with proper filename

---

## Debugging Steps

### 1. Check Backend Logs

Look for log messages like:
```
Uploading file: resume.pdf, extension: .pdf, content_type: application/pdf, size: 1234567
File size: 1234567 bytes (1.18 MB)
```

### 2. Test with curl

```bash
curl -X POST "http://localhost:8000/api/v1/cvs/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_resume.pdf"
```

### 3. Check Frontend Console

Open browser DevTools → Network tab → Check the request:
- Request payload should be FormData
- File should be included
- Content-Type should be `multipart/form-data`

### 4. Verify File Format

```bash
# Check file type
file resume.pdf
# Should show: PDF document

# Check file size
ls -lh resume.pdf
```

---

## Frontend Issues

### Issue: File not being sent correctly

**Check:**
1. File input is properly bound
2. FormData is created correctly
3. File is included in FormData

**Example:**
```typescript
const formData = new FormData()
formData.append('file', file)  // 'file' must match backend parameter name
```

### Issue: Content-Type header

**Note:** Don't manually set `Content-Type` header for FormData - browser sets it automatically with boundary.

---

## Backend Issues

### Issue: Storage bucket doesn't exist

**Error:** "Failed to upload file to storage"

**Solution:**
1. Create `cvs` bucket in Supabase Dashboard
2. Set bucket to Private
3. Run storage policies SQL

### Issue: Storage permissions

**Error:** "Permission denied" or "Access denied"

**Solution:**
1. Run `docs/SUPABASE_STORAGE_POLICIES.sql`
2. Verify RLS policies are active
3. Check service role key is correct

---

## Quick Fixes

### If file extension is wrong:
```python
# Backend accepts: .pdf, .docx (case-insensitive)
# Make sure frontend sends correct extension
```

### If file size issue:
```python
# Max size: 10MB (10 * 1024 * 1024 bytes)
# Check file size before upload
```

### If storage error:
```python
# Check SUPABASE_STORAGE_BUCKET in .env
# Default: "cvs"
# Verify bucket exists in Supabase Dashboard
```

---

## Testing Checklist

- [ ] File has `.pdf` or `.docx` extension
- [ ] File size < 10MB
- [ ] File is not empty
- [ ] Storage bucket exists
- [ ] Storage policies are set
- [ ] Service role key is correct
- [ ] Frontend sends FormData correctly
- [ ] Backend logs show file details

---

## Still Having Issues?

1. Check backend terminal output for detailed error messages
2. Check browser console for frontend errors
3. Verify Supabase Storage bucket configuration
4. Test with a simple PDF file first
5. Check network tab in browser DevTools

