import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { copyFileSync, mkdirSync } from 'fs'
import { join } from 'path'

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'copy-html-files',
      writeBundle() {
        // Copy HTML files to dist folder
        const htmlFiles = ['config-popup.html', 'visualizer.html']
        const srcDir = 'src/renderer'
        const distDir = 'dist/renderer'
        
        htmlFiles.forEach(file => {
          try {
            copyFileSync(join(srcDir, file), join(distDir, file))
            console.log(`Copied ${file} to dist folder`)
          } catch (error) {
            console.error(`Failed to copy ${file}:`, error)
          }
        })
      }
    }
  ],
  base: './',
  root: '.',
  build: {
    outDir: 'dist/renderer',
    emptyOutDir: true
  },
  server: {
    port: 5174
  }
})
