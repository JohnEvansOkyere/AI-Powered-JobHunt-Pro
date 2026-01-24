/**
 * Utility functions for safely parsing JSON data from the backend
 */

/**
 * Safely parse a JSON string into an array of strings
 * Returns empty array if parsing fails or input is invalid
 * 
 * @param jsonString - JSON string from backend (may be null, undefined, or malformed)
 * @returns Array of strings, or empty array if parsing fails
 */
export function parseJsonArray(jsonString: string | null | undefined): string[] {
  // Handle null/undefined
  if (!jsonString) return []
  
  // Handle non-string values
  if (typeof jsonString !== 'string') {
    console.warn('parseJsonArray: Expected string, got', typeof jsonString)
    return []
  }
  
  // Handle empty or special strings
  const trimmed = jsonString.trim()
  if (trimmed === '' || trimmed === 'null' || trimmed === 'undefined') {
    return []
  }
  
  try {
    const parsed = JSON.parse(trimmed)
    
    // Ensure result is an array
    if (!Array.isArray(parsed)) {
      console.warn('parseJsonArray: Parsed value is not an array:', parsed)
      return []
    }
    
    // Filter out non-string and empty items
    return parsed.filter(item => typeof item === 'string' && item.trim() !== '')
  } catch (error) {
    console.error('parseJsonArray: Failed to parse JSON:', {
      input: jsonString.substring(0, 100), // Log first 100 chars
      error: error instanceof Error ? error.message : String(error)
    })
    return []
  }
}

/**
 * Safely parse a JSON string into an object
 * Returns empty object if parsing fails
 * 
 * @param jsonString - JSON string from backend
 * @returns Parsed object, or empty object if parsing fails
 */
export function parseJsonObject<T = Record<string, any>>(
  jsonString: string | null | undefined,
  defaultValue: T = {} as T
): T {
  if (!jsonString) return defaultValue
  if (typeof jsonString !== 'string') return defaultValue
  
  const trimmed = jsonString.trim()
  if (trimmed === '' || trimmed === 'null' || trimmed === 'undefined') {
    return defaultValue
  }
  
  try {
    const parsed = JSON.parse(trimmed)
    return parsed as T
  } catch (error) {
    console.error('parseJsonObject: Failed to parse JSON:', {
      input: jsonString.substring(0, 100),
      error: error instanceof Error ? error.message : String(error)
    })
    return defaultValue
  }
}

/**
 * Validate if a string is valid JSON
 * 
 * @param jsonString - String to validate
 * @returns true if valid JSON, false otherwise
 */
export function isValidJson(jsonString: string | null | undefined): boolean {
  if (!jsonString || typeof jsonString !== 'string') return false
  
  const trimmed = jsonString.trim()
  if (trimmed === '') return false
  
  try {
    JSON.parse(trimmed)
    return true
  } catch {
    return false
  }
}
