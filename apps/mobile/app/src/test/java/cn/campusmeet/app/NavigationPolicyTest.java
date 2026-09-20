package cn.campusmeet.app;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class NavigationPolicyTest {
    @Test
    public void keepsOnlyCampusMeetProductionPagesInsideTheApp() {
        assertTrue(NavigationPolicy.isInternal("https://campusmate-web.onrender.com"));
        assertTrue(NavigationPolicy.isInternal("https://campusmate-web.onrender.com/posts/3"));
        assertFalse(NavigationPolicy.isInternal("http://campusmate-web.onrender.com"));
        assertFalse(NavigationPolicy.isInternal("https://example.com/campusmate-web.onrender.com"));
        assertFalse(NavigationPolicy.isInternal("mailto:team@example.com"));
        assertFalse(NavigationPolicy.isInternal("not a url"));
    }
}
