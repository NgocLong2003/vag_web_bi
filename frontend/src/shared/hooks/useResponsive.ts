import { useState, useEffect } from 'react'

type Breakpoint = 'mobile' | 'tablet' | 'desktop'

interface ResponsiveState {
  isMobile: boolean
  isTablet: boolean
  isDesktop: boolean
  isLandscapePhone: boolean
  breakpoint: Breakpoint
  width: number
  height: number
}

export function useResponsive(): ResponsiveState {
  const [state, setState] = useState<ResponsiveState>(getState)

  useEffect(() => {
    function onResize() {
      setState(getState())
    }
    window.addEventListener('resize', onResize)
    window.addEventListener('orientationchange', () => setTimeout(onResize, 300))
    return () => {
      window.removeEventListener('resize', onResize)
      window.removeEventListener('orientationchange', onResize)
    }
  }, [])

  return state
}

function getState(): ResponsiveState {
  const w = window.innerWidth
  const h = window.innerHeight
  const isMobile = w <= 768
  const isTablet = w > 768 && w <= 1024
  const isDesktop = w > 1024
  const isLandscapePhone =
    w > h && h <= 500 && window.matchMedia('(hover: none)').matches

  return {
    isMobile: isMobile || isLandscapePhone,
    isTablet,
    isDesktop,
    isLandscapePhone,
    breakpoint: isMobile || isLandscapePhone ? 'mobile' : isTablet ? 'tablet' : 'desktop',
    width: w,
    height: h,
  }
}
