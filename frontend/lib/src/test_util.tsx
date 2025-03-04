/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* eslint-disable import/no-extraneous-dependencies */
import {
  render as reactTestingLibraryRender,
  RenderOptions,
  RenderResult,
} from "@testing-library/react"
import {
  mount as enzymeMount,
  MountRendererProps,
  ReactWrapper,
  shallow as enzymeShallow,
  ShallowRendererProps,
  ShallowWrapper,
} from "enzyme"
/* eslint-enable */
import React, { Component, FC, ReactElement } from "react"
import ThemeProvider from "./components/core/ThemeProvider"
import { baseTheme, EmotionTheme } from "./theme"
import { mockTheme } from "./mocks/mockTheme"
import { LibContext, LibContextProps } from "./components/core/LibContext"

export function mount<C extends Component, P = C["props"], S = C["state"]>(
  node: ReactElement<P>,
  options?: MountRendererProps,
  theme?: EmotionTheme
): ReactWrapper<P, S, C> {
  const opts: MountRendererProps = {
    ...(options || {}),
    wrappingComponent: ThemeProvider,
    wrappingComponentProps: {
      theme: theme || mockTheme.emotion,
    },
  }

  return enzymeMount(node, opts)
}

export function shallow<C extends Component, P = C["props"], S = C["state"]>(
  node: ReactElement<P>,
  options?: ShallowRendererProps,
  theme?: EmotionTheme
): ShallowWrapper<P, S, C> {
  const opts: ShallowRendererProps = {
    ...(options || {}),
    wrappingComponent: ThemeProvider,
    wrappingComponentProps: {
      theme: theme || mockTheme.emotion,
    },
  }

  return enzymeShallow(node, opts)
}

const RenderWrapper: FC = ({ children }) => {
  return <ThemeProvider theme={mockTheme.emotion}>{children}</ThemeProvider>
}

/**
 * Use react-testing-library to render a ReactElement. The element will be
 * wrapped in our ThemeProvider.
 */
export function render(
  ui: ReactElement,
  options?: Omit<RenderOptions, "queries">
): RenderResult {
  return reactTestingLibraryRender(ui, {
    wrapper: RenderWrapper,
    ...options,
  })
}

export function mockWindowLocation(hostname: string): void {
  // Mock window.location by creating a new object
  // Source: https://www.benmvp.com/blog/mocking-window-location-methods-jest-jsdom/
  // @ts-expect-error
  delete window.location

  // @ts-expect-error
  window.location = {
    assign: jest.fn(),
    hostname: hostname,
  }
}

/**
 * Use react-testing-library to render a ReactElement. The element will be
 * wrapped in our LibContext.Provider.
 */
export const customRenderLibContext = (
  component: ReactElement,
  overrideLibContextProps: Partial<LibContextProps>
): RenderResult => {
  const defaultLibContextProps = {
    isFullScreen: false,
    setFullScreen: jest.fn(),
    addScriptFinishedHandler: jest.fn(),
    removeScriptFinishedHandler: jest.fn(),
    activeTheme: baseTheme,
    setTheme: jest.fn(),
    availableThemes: [],
    addThemes: jest.fn(),
    hideFullScreenButtons: false,
    libConfig: {},
  }

  return reactTestingLibraryRender(component, {
    wrapper: ({ children }) => (
      <ThemeProvider theme={baseTheme.emotion}>
        <LibContext.Provider
          value={{ ...defaultLibContextProps, ...overrideLibContextProps }}
        >
          {children}
        </LibContext.Provider>
      </ThemeProvider>
    ),
  })
}
