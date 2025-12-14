'use client'

import { useState } from 'react'
import { Filter, X } from 'lucide-react'

interface JobFiltersProps {
  onFilterChange: (filters: FilterState) => void
}

export interface FilterState {
  jobTitle: string
  location: string
  workType: string[]
  seniority: string[]
  salaryRange: string
  datePosted: string
}

const workTypes = ['Remote', 'Hybrid', 'On-site']
const seniorityLevels = ['Entry', 'Mid', 'Senior', 'Lead', 'Executive']
const salaryRanges = [
  'Any',
  '$0 - $50k',
  '$50k - $100k',
  '$100k - $150k',
  '$150k+',
]
const dateRanges = ['Any', 'Last 24 hours', 'Last week', 'Last month']

export function JobFilters({ onFilterChange }: JobFiltersProps) {
  const [filters, setFilters] = useState<FilterState>({
    jobTitle: '',
    location: '',
    workType: [],
    seniority: [],
    salaryRange: 'Any',
    datePosted: 'Any',
  })

  const [isOpen, setIsOpen] = useState(true)

  const updateFilter = (key: keyof FilterState, value: any) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }

  const toggleArrayFilter = (key: 'workType' | 'seniority', value: string) => {
    const current = filters[key] as string[]
    const newValue = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value]
    updateFilter(key, newValue)
  }

  const clearFilters = () => {
    const cleared = {
      jobTitle: '',
      location: '',
      workType: [],
      seniority: [],
      salaryRange: 'Any',
      datePosted: 'Any',
    }
    setFilters(cleared)
    onFilterChange(cleared)
  }

  const hasActiveFilters =
    filters.jobTitle ||
    filters.location ||
    filters.workType.length > 0 ||
    filters.seniority.length > 0 ||
    filters.salaryRange !== 'Any' ||
    filters.datePosted !== 'Any'

  return (
    <div className="bg-white rounded-lg shadow-sm border border-neutral-200">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200">
        <div className="flex items-center space-x-2">
          <Filter className="h-5 w-5 text-neutral-500" />
          <h3 className="font-semibold text-neutral-800">Filters</h3>
        </div>
        <div className="flex items-center space-x-2">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              Clear all
            </button>
          )}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="lg:hidden text-neutral-500 hover:text-neutral-700"
          >
            {isOpen ? <X className="h-5 w-5" /> : <Filter className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Filter Content */}
      {isOpen && (
        <div className="p-4 space-y-6">
          {/* Job Title */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Job Title
            </label>
            <input
              type="text"
              value={filters.jobTitle}
              onChange={(e) => updateFilter('jobTitle', e.target.value)}
              placeholder="e.g. Software Engineer"
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Location */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Location
            </label>
            <input
              type="text"
              value={filters.location}
              onChange={(e) => updateFilter('location', e.target.value)}
              placeholder="e.g. New York, Remote"
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Work Type */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Work Type
            </label>
            <div className="space-y-2">
              {workTypes.map((type) => (
                <label
                  key={type}
                  className="flex items-center space-x-2 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={filters.workType.includes(type)}
                    onChange={() => toggleArrayFilter('workType', type)}
                    className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500"
                  />
                  <span className="text-sm text-neutral-700">{type}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Seniority Level */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Seniority Level
            </label>
            <div className="space-y-2">
              {seniorityLevels.map((level) => (
                <label
                  key={level}
                  className="flex items-center space-x-2 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={filters.seniority.includes(level)}
                    onChange={() => toggleArrayFilter('seniority', level)}
                    className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500"
                  />
                  <span className="text-sm text-neutral-700">{level}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Salary Range */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Salary Range
            </label>
            <select
              value={filters.salaryRange}
              onChange={(e) => updateFilter('salaryRange', e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {salaryRanges.map((range) => (
                <option key={range} value={range}>
                  {range}
                </option>
              ))}
            </select>
          </div>

          {/* Date Posted */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Date Posted
            </label>
            <select
              value={filters.datePosted}
              onChange={(e) => updateFilter('datePosted', e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {dateRanges.map((range) => (
                <option key={range} value={range}>
                  {range}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  )
}

