import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('working digest processes user input, follows sources and downloads a handoff', async ({page}) => {
  const external = [];
  page.on('request', r => { if(!r.url().startsWith('http://127.0.0.1:8765')) external.push(r.url()); });
  await page.goto('/workspace');
  await page.getByRole('link', {name: 'Try the working thread digest'}).click();
  await expect(page.getByText(/SYNTHETIC example loaded/)).toBeVisible();
  await page.getByLabel('Discussion', {exact:true}).fill("maya: Is the security review complete?\nleo: Decided: use a blue logo.\nmaya: I'll prepare the release notes.");
  await page.getByRole('button', {name: 'Make the digest'}).click();
  await expect(page.locator('#digest')).toBeVisible();
  await expect(page.locator('.result-card').filter({has: page.getByRole('heading', {name:'Questions to review'})})).toContainText('Is the security review complete?');
  await page.locator('.result-card a[href="#m2"]').click();
  await expect(page.locator('#m2')).toBeInViewport();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', {name:'Download Markdown'}).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('thread-digest.md');
  const stream = await download.createReadStream();
  const chunks=[]; for await (const chunk of stream) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString('utf8');
  expect(text).toContain('maya: Is the security review complete?');
  expect(text).toContain('## Source messages');
  expect(external).toEqual([]);
});

test('digest is accessible on mobile and hostile source markup stays text', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/mvp');
  await page.getByLabel('Discussion', {exact:true}).fill('eve: Decided: <script>window.bad=true</script>\nlee: What about security?');
  await page.getByRole('button', {name:'Make the digest'}).click();
  expect(await page.evaluate(() => window.bad)).toBeUndefined();
  await expect(page.locator('#m1')).toContainText('<script>');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:'../../.pytest_cache/mvp-mobile.png', fullPage:true});
});

test('synthetic sample yields a real digest without claiming validation', async ({page}) => {
  await page.goto('/mvp');
  await page.getByRole('button', {name:'Make the digest'}).click();
  await expect(page.locator('#digest')).toContainText('6');
  await expect(page.getByText(/SYNTHETIC example loaded/)).toBeVisible();
  await expect(page.locator('.result-card').filter({has:page.getByRole('heading', {name:'Decisions', exact:true})})).not.toContainText('not decided');
  await expect(page.locator('footer')).toContainText('not proof of demand');
  await page.screenshot({path:'../../.pytest_cache/mvp-desktop.png', fullPage:true});
});
