# Tailwind CSS Setup Guide

This guide explains how to set up Tailwind CSS in the Next.js project.

---

## Installation (Current Project Already Has It)

The project already has Tailwind installed. These are the installed packages:

```json
{
  "tailwindcss": "^4",
  "@tailwindcss/postcss": "^4.2.1"
}
```

---

## Fresh Setup (If Starting from Scratch)

If you were starting a new project from scratch, follow these steps:

### 1. Install Dependencies

```bash
npm install tailwindcss @tailwindcss/postcss postcss
```

### 2. Create postcss.config.js

Create `postcss.config.js` in the project root:

```javascript
/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
};

module.exports = config;
```

### 3. Update globals.css

In `src/app/globals.css`, add at the top:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

## Common Tailwind CSS Classes Reference

### Layout
| Class | Description |
|-------|-------------|
| `flex` | Display: flex |
| `grid` | Display: grid |
| `flex-col` | Flex direction: column |
| `flex-wrap` | Flex wrap: wrap |
| `items-center` | Align items: center |
| `justify-between` | Justify content: space-between |
| `justify-center` | Justify content: center |
| `gap-4` | Gap: 1rem (gap between items) |
| `gap-6` | Gap: 1.5rem |

### Sizing
| Class | Description |
|-------|-------------|
| `w-64` | Width: 16rem |
| `w-1/2` | Width: 50% |
| `h-16` | Height: 4rem |
| `min-h-screen` | Min height: 100vh |

### Spacing
| Class | Description |
|-------|-------------|
| `p-4` | Padding: 1rem |
| `p-6` | Padding: 1.5rem |
| `m-4` | Margin: 1rem |
| `mb-4` | Margin bottom: 1rem |
| `mt-6` | Margin top: 1.5rem |

### Colors (Background & Text)
| Class | Description |
|-------|-------------|
| `bg-white` | Background: white |
| `bg-gray-50` | Background: #f9fafb |
| `bg-gray-100` | Background: #f3f4f6 |
| `bg-blue-500` | Background: #3b82f6 |
| `bg-red-50` | Background: #fef2f2 |
| `text-white` | Text: white |
| `text-gray-900` | Text: #111827 |
| `text-gray-500` | Text: #6b7280 |
| `text-blue-600` | Text: #2563eb |
| `text-red-600` | Text: #dc2626 |

### Borders
| Class | Description |
|-------|-------------|
| `border` | Border: 1px solid |
| `border-gray-200` | Border color: #e5e7eb |
| `border-r` | Border right |
| `border-b` | Border bottom |

### Border Radius (Rounded Corners)
| Class | Description |
|-------|-------------|
| `rounded` | Border radius: 0.25rem |
| `rounded-lg` | Border radius: 0.5rem |
| `rounded-xl` | Border radius: 0.75rem |
| `rounded-full` | Border radius: 9999px (circle) |

### Shadows
| Class | Description |
|-------|-------------|
| `shadow-sm` | Box shadow: small |
| `shadow` | Box shadow: medium |
| `shadow-lg` | Box shadow: large |

### Typography
| Class | Description |
|-------|-------------|
| `text-sm` | Font size: 0.875rem |
| `text-lg` | Font size: 1.125rem |
| `text-xl` | Font size: 1.25rem |
| `text-2xl` | Font size: 1.5rem |
| `text-3xl` | Font size: 1.875rem |
| `font-bold` | Font weight: 700 |
| `font-semibold` | Font weight: 600 |
| `font-medium` | Font weight: 500 |

### Responsive Prefixes
| Prefix | Breakpoint |
|--------|------------|
| `sm:` | 640px |
| `md:` | 768px |
| `lg:` | 1024px |
| `xl:` | 1280px |

Example:
```jsx
// On mobile: 1 column, on md (768px+): 2 columns, on lg (1024px+): 4 columns
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
```

---

## Quick Examples

### Card Component
```jsx
<div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
  <h3 className="font-semibold text-lg text-gray-900 mb-2">Title</h3>
  <p className="text-gray-500 text-sm">Description</p>
</div>
```

### Grid Layout
```jsx
<div className="grid grid-cols-2 gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
  <div>Item 4</div>
</div>
```

### Flex Row with Center Alignment
```jsx
<div className="flex items-center justify-between">
  <div>Left</div>
  <div>Right</div>
</div>
```

### Button
```jsx
<button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
  Click Me
</button>
```

### Sidebar Layout
```jsx
<div className="flex min-h-screen">
  <aside className="w-64 bg-white border-r border-gray-200">
    {/* Sidebar content */}
  </aside>
  <main className="flex-1 bg-gray-50 p-6">
    {/* Main content */}
  </main>
</div>
```

---

## Official Resources

- **Documentation**: https://tailwindcss.com/docs
- **Search Classes**: https://tailwindcss.com/docs/utility-first
- **Interactive Playground**: https://play.tailwindcss.com/
