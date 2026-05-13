import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { cn } from '@/lib/utils'
import { X, Plus, Upload, Calendar, User, Building } from 'lucide-react'

// Form schemas
export const assetSchema = z.object({
  assetName: z.string().min(1, 'Asset name is required'),
  therapeuticArea: z.string().min(1, 'Therapeutic area is required'),
  trialPhase: z.string().min(1, 'Trial phase is required'),
  costPerPatient: z.number().min(0, 'Cost must be positive'),
  totalEstimatedCost: z.number().min(0, 'Total cost must be positive'),
  projectedRevenue: z.number().min(0, 'Projected revenue must be positive'),
  description: z.string().optional(),
  startDate: z.date().optional(),
  endDate: z.date().optional()
})

export const trialSchema = z.object({
  title: z.string().min(1, 'Trial title is required'),
  therapeuticArea: z.string().min(1, 'Therapeutic area is required'),
  phase: z.string().min(1, 'Phase is required'),
  status: z.string().min(1, 'Status is required'),
  primaryEndpoint: z.string().min(1, 'Primary endpoint is required'),
  secondaryEndpoints: z.array(z.string()).optional(),
  inclusionCriteria: z.string().min(1, 'Inclusion criteria is required'),
  exclusionCriteria: z.string().min(1, 'Exclusion criteria is required'),
  targetEnrollment: z.number().min(1, 'Target enrollment must be positive'),
  estimatedDuration: z.number().min(1, 'Duration must be positive'),
  budget: z.number().min(0, 'Budget must be positive')
})

// Modal component
interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export function Modal({ isOpen, onClose, title, children, size = 'md', className }: ModalProps) {
  if (!isOpen) return null

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl'
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className={cn(
          'inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle w-full',
          sizeClasses[size],
          className
        )}>
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

// Form input component
interface FormInputProps {
  label: string
  error?: string
  required?: boolean
  children: React.ReactNode
}

export function FormInput({ label, error, required, children }: FormInputProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}

// Asset form component
interface AssetFormProps {
  onSubmit: (data: z.infer<typeof assetSchema>) => void
  onCancel: () => void
  initialData?: Partial<z.infer<typeof assetSchema>>
  title?: string
}

export function AssetForm({ onSubmit, onCancel, initialData, title = "Add New Asset" }: AssetFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<z.infer<typeof assetSchema>>({
    resolver: zodResolver(assetSchema),
    defaultValues: initialData
  })

  const therapeuticAreas = [
    'Oncology', 'Cardiology', 'Neurology', 'Immunology', 'Endocrinology',
    'Dermatology', 'Gastroenterology', 'Respiratory', 'Infectious Diseases', 'Rare Diseases'
  ]

  const trialPhases = [
    'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Preclinical', 'IND'
  ]

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FormInput label="Asset Name" error={errors.assetName?.message} required>
          <input
            {...register('assetName')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter asset name"
          />
        </FormInput>

        <FormInput label="Therapeutic Area" error={errors.therapeuticArea?.message} required>
          <select
            {...register('therapeuticArea')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select therapeutic area</option>
            {therapeuticAreas.map(area => (
              <option key={area} value={area}>{area}</option>
            ))}
          </select>
        </FormInput>

        <FormInput label="Trial Phase" error={errors.trialPhase?.message} required>
          <select
            {...register('trialPhase')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select trial phase</option>
            {trialPhases.map(phase => (
              <option key={phase} value={phase}>{phase}</option>
            ))}
          </select>
        </FormInput>

        <FormInput label="Cost per Patient" error={errors.costPerPatient?.message} required>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
            <input
              {...register('costPerPatient', { valueAsNumber: true })}
              type="number"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0"
            />
          </div>
        </FormInput>

        <FormInput label="Total Estimated Cost" error={errors.totalEstimatedCost?.message} required>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
            <input
              {...register('totalEstimatedCost', { valueAsNumber: true })}
              type="number"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0"
            />
          </div>
        </FormInput>

        <FormInput label="Projected Revenue" error={errors.projectedRevenue?.message} required>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
            <input
              {...register('projectedRevenue', { valueAsNumber: true })}
              type="number"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0"
            />
          </div>
        </FormInput>
      </div>

      <FormInput label="Description" error={errors.description?.message}>
        <textarea
          {...register('description')}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter asset description"
        />
      </FormInput>

      <div className="flex items-center justify-end space-x-4 pt-6 border-t border-gray-200">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? 'Saving...' : 'Save Asset'}
        </button>
      </div>
    </form>
  )
}

// Trial form component
interface TrialFormProps {
  onSubmit: (data: z.infer<typeof trialSchema>) => void
  onCancel: () => void
  initialData?: Partial<z.infer<typeof trialSchema>>
  title?: string
}

export function TrialForm({ onSubmit, onCancel, initialData, title = "Add New Trial" }: TrialFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<z.infer<typeof trialSchema>>({
    resolver: zodResolver(trialSchema),
    defaultValues: initialData
  })

  const phases = ['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4']
  const statuses = ['Design', 'Recruiting', 'Active', 'Completed', 'Terminated', 'On Hold']

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <FormInput label="Trial Title" error={errors.title?.message} required>
          <input
            {...register('title')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter trial title"
          />
        </FormInput>

        <FormInput label="Therapeutic Area" error={errors.therapeuticArea?.message} required>
          <input
            {...register('therapeuticArea')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter therapeutic area"
          />
        </FormInput>

        <FormInput label="Phase" error={errors.phase?.message} required>
          <select
            {...register('phase')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select phase</option>
            {phases.map(phase => (
              <option key={phase} value={phase}>{phase}</option>
            ))}
          </select>
        </FormInput>

        <FormInput label="Status" error={errors.status?.message} required>
          <select
            {...register('status')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select status</option>
            {statuses.map(status => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
        </FormInput>

        <FormInput label="Target Enrollment" error={errors.targetEnrollment?.message} required>
          <input
            {...register('targetEnrollment', { valueAsNumber: true })}
            type="number"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="0"
          />
        </FormInput>

        <FormInput label="Estimated Duration (months)" error={errors.estimatedDuration?.message} required>
          <input
            {...register('estimatedDuration', { valueAsNumber: true })}
            type="number"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="0"
          />
        </FormInput>

        <FormInput label="Budget" error={errors.budget?.message} required>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
            <input
              {...register('budget', { valueAsNumber: true })}
              type="number"
              className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0"
            />
          </div>
        </FormInput>
      </div>

      <FormInput label="Primary Endpoint" error={errors.primaryEndpoint?.message} required>
        <input
          {...register('primaryEndpoint')}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter primary endpoint"
        />
      </FormInput>

      <FormInput label="Inclusion Criteria" error={errors.inclusionCriteria?.message} required>
        <textarea
          {...register('inclusionCriteria')}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter inclusion criteria"
        />
      </FormInput>

      <FormInput label="Exclusion Criteria" error={errors.exclusionCriteria?.message} required>
        <textarea
          {...register('exclusionCriteria')}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter exclusion criteria"
        />
      </FormInput>

      <div className="flex items-center justify-end space-x-4 pt-6 border-t border-gray-200">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? 'Saving...' : 'Save Trial'}
        </button>
      </div>
    </form>
  )
}






















